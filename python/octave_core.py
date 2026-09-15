# Copyright (C) 2026 Andreas Bertsatos <abertsatos@biol.uoa.gr>
#
# This file is part of the octave-calc extension.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

"""Running Octave, and nothing about LibreOffice.

Everything here is testable from a plain Python prompt, which is the point:
the office-facing files hold no logic worth testing and this file holds no UNO
call.  It is shared by the Add-In component and the menu-driven workbench.

Arguments are built as devtools' octave_call takes them: a list in call order
of numbers, strings, logical values and ranges, each range cell carrying its
kind and value, dates and times as serial numbers from the document's null
date.

Every call runs in a sandboxed devtools.mcpEval server, on Linux only.  No
cell is evaluated where no sandbox can run, and none by a server that does
not report its sandbox.
"""

import atexit
import hashlib
import json
import os
import re
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time

OCTAVE_CANDIDATES = ('octave-cli',)

# A bare function name, or a namespaced or static-method one: mean, geom.area,
# ClassName.method.  Anything else never reaches the interpreter.
NAME_RE = re.compile (r'^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)*$')

OCTAVE_FLAGS = ('-q', '--no-init-file', '--no-site-file', '--no-history')

# The server, launched as devtools documents it.  What it may read and load,
# and its budgets, travel in the environment, never in this text.
LAUNCH = "pkg load devtools; devtools.mcpEval ('Sandbox', true)"

# A sandboxed server reports itself under this key of its results' _meta.
SANDBOX_KEY = 'io.github.pr0m1th3as.devtools/sandbox'

PROTOCOL_VERSION = '2025-11-25'

# What a server launched through systemd-run takes from this environment,
# since systemd-run passes none of it on.  The sandbox clears everything
# inside except HOME and LANG.
PASSED = ('PATH', 'HOME', 'LANG', 'LD_LIBRARY_PATH')

# How long a server may take to start, and how long past its own deadline a
# call may go unanswered before the server is taken to be stuck.
START_SECONDS = 60
GRACE_SECONDS = 5

# Serial number 0 when a document does not say otherwise.
NULL_DATE = '1899-12-30'

# com.sun.star.util.NumberFormat bits and a com.sun.star.sheet.FormulaResult
# value, copied here so that this file needs no UNO.
FORMAT_DATE = 2
FORMAT_TIME = 4
FORMAT_LOGICAL = 1024
FORMAT_DURATION = 8192
RESULT_STRING = 2

# What Calc shows for an error code, as ScGlobal::GetErrorString gives it in
# English.  Any other code shows as Err: and the number.
ERROR_NAMES = {503: '#NUM!', 519: '#VALUE!', 521: '#NULL!', 524: '#REF!',
               525: '#NAME?', 530: '#ADDIN?', 531: '#MACRO?', 532: '#DIV/0!',
               32767: '#N/A'}

# #N/A: a missing value both ways.  A NaN result shows as #N/A, and #N/A in a
# range read through OCTRANGE is missing, as an empty cell is.
ERROR_NOT_AVAILABLE = 32767

# An OCTRANGE key: this prefix, the mode, the range's absolute name, then the
# SHA-1 of its cells.  A sheet name may hold '|', so the mode is split off the
# left and the digest off the right.
KEY_PREFIX = 'octrange|'

# How OCTAVE uses a range: as one argument, or expanded into name-value pairs.
MODES = ('data', 'pairs')

# What a cell shows when this extension refuses or fails.  One such text
# passed on to another formula is refused in turn, never sent to Octave.
MESSAGE_PREFIX = 'octave-calc: '

# The arguments an OCTAVE formula can pass, as idl/octave_calc.idl declares.
MAX_ARGS = 16

# A time format showing elapsed hours, minutes or seconds, as [HH]:MM:SS does.
# Calc reports it as a time, like a time of day.
ELAPSED_RE = re.compile (r'\[(h+|m+|s+)\]', re.IGNORECASE)

# A formula cannot use a thread, so a recalculation blocks.  The cache is what
# makes that bearable: one that changes no input runs no interpreter at all.
_CACHE = {}
_CACHE_ORDER = []
_CACHE_LIMIT = 200

# Ranges read by OCTRANGE, under their keys.  One that has been dropped is
# read again from the address in its key.
_RANGES = {}
_RANGES_ORDER = []
_RANGES_LIMIT = 200


def octave ():
  """Absolute path to an Octave interpreter, or None."""
  for name in OCTAVE_CANDIDATES:
    found = shutil.which (name)
    if (found):
      return found
  return None


def octave_version (binary):
  probe = subprocess.run (list ((binary,) + OCTAVE_FLAGS)
                          + ['--eval', 'disp (version ());'],
                          capture_output = True, text = True, timeout = 60)
  return probe.stdout.strip ()


def as_rows (data):
  """Whatever the office handed over, as a tuple of row tuples."""
  if (not isinstance (data, (list, tuple))):
    return ((data,),)
  if (data and isinstance (data[0], (list, tuple))):
    return tuple (tuple (row) for row in data)
  return (tuple (data),)


def error_name (code):
  """What Calc shows in a cell holding the error CODE."""
  return ERROR_NAMES.get (code, 'Err:%d' % code)


def cell_kind (content, result, error, value, text, format_type,
               format_string):
  """One range cell from what Calc reports about it.

  CONTENT is the name of the cell's CellContentType, RESULT its
  FormulaResultType2, ERROR its error code, VALUE and TEXT its value and
  displayed text, and FORMAT_TYPE and FORMAT_STRING its number format.  A
  formula's result is read by the format it is shown with.  An error is named
  from its code, since the displayed text reads '...' while Calc
  recalculates.  #N/A is a missing value, marked so that a pair can tell it
  from a blank cell."""
  if (error == ERROR_NOT_AVAILABLE):
    return {'kind': 'empty', 'na': True}
  if (error):
    return {'kind': 'error', 'value': error_name (error)}
  if (content == 'EMPTY'):
    return {'kind': 'empty'}
  if (content == 'TEXT' or (content == 'FORMULA' and result == RESULT_STRING)):
    return {'kind': 'text', 'value': text}
  value = float (value)
  if (format_type & FORMAT_LOGICAL):
    return {'kind': 'logical', 'value': value != 0}
  if (format_type & FORMAT_DURATION):
    return {'kind': 'duration', 'value': value}
  if (format_type & FORMAT_DATE):
    if (format_type & FORMAT_TIME):
      return {'kind': 'datetime', 'value': value}
    return {'kind': 'date', 'value': value}
  if (format_type & FORMAT_TIME):
    if (ELAPSED_RE.search (format_string)):
      return {'kind': 'duration', 'value': value}
    return {'kind': 'time', 'value': value}
  return {'kind': 'number', 'value': value}


# Text a spreadsheet holds in place of a non-finite number.  datatypes writes
# an infinity to ODS and XLSX this way, since Calc loads a non-finite number
# from a file as 0.
NUMBER_TEXTS = {'inf': float ('inf'), '-inf': float ('-inf'),
                'nan': float ('nan')}


def number_text (cell):
  return cell['kind'] == 'text' and cell['value'].lower () in NUMBER_TEXTS


def numeric_texts (rows):
  """ROWS with each text cell reading Inf, -Inf or NaN, in any capitals, made
  that number, when every other cell of the range is a number or empty.  Any
  other range comes back as it was."""
  cells = [cell for row in rows for cell in row]
  if (not any (number_text (cell) for cell in cells)
      or any (not number_text (cell) and cell['kind'] not in ('number', 'empty')
              for cell in cells)):
    return rows
  return [[{'kind': 'number', 'value': NUMBER_TEXTS[cell['value'].lower ()]}
           if number_text (cell) else cell for cell in row] for row in rows]


def plain_cell (value):
  """A range cell known by its value alone, as getDataArray and a sequence
  argument deliver it, where an empty cell is empty text."""
  if (value is None or value == ''):
    return {'kind': 'empty'}
  if (isinstance (value, str)):
    return {'kind': 'text', 'value': value}
  return {'kind': 'number', 'value': float (value)}


def range_arg (rows):
  """A range argument from rows of cells as cell_kind builds them."""
  return {'type': 'range', 'rows': len (rows), 'cols': len (rows[0]),
          'cells': [cell for row in rows for cell in row]}


def plain_range (data):
  """A range argument from values alone."""
  return range_arg ([[plain_cell (value) for value in row]
                     for row in as_rows (data)])


def build_args (args, resolve):
  """The octave_call arguments of an OCTAVE formula from ARGS as Calc gives
  them.  Omitted arguments at the end are dropped.  An OCTRANGE key becomes
  its range, or its name-value pairs, through RESOLVE, which returns the
  range's top-left column and row and its rows of cells; anything else is
  taken by value.  Raises ValueError."""
  args = list (args or ())
  while (args and args[-1] is None):
    args.pop ()
  built = []
  for position, value in enumerate (args, 1):
    if (value is None):
      raise ValueError ('argument %d is empty.' % position)
    if (isinstance (value, str) and value.startswith (MESSAGE_PREFIX)):
      raise ValueError (value[len (MESSAGE_PREFIX):])
    if (isinstance (value, str) and value.startswith (KEY_PREFIX)):
      mode, column, row, rows = key_range (value, resolve)
      if (mode == 'pairs'):
        built.extend (expand_pairs (rows, column, row, resolve))
      else:
        built.append (range_arg (rows))
    elif (isinstance (value, (list, tuple))):
      built.append (plain_range (value))
    elif (isinstance (value, str)):
      built.append ({'type': 'string', 'value': value})
    elif (isinstance (value, bool)):
      built.append ({'type': 'logical', 'value': value})
    else:
      built.append ({'type': 'number', 'value': float (value)})
  return built


def key_range (key, resolve):
  """The mode, top-left column and row, and rows of cells behind an OCTRANGE
  KEY.  Refuses a malformed key and a range holding an error cell."""
  parts = key_parts (key)
  if (parts is None):
    raise ValueError ('"%s" is not an OCTRANGE key.' % key)
  column, row, rows = resolve (key)
  refusal = refuse_errors (rows, column, row)
  if (refusal):
    raise ValueError (refusal)
  return parts[0], column, row, rows


def expand_pairs (rows, column, row, resolve):
  """The name-value arguments of a "pairs" range whose top-left cell is at
  COLUMN and ROW: a name in the first column, its value in the second, one
  pair per row.  A row with no name is skipped."""
  if (len (rows[0]) != 2):
    raise ValueError ('the "pairs" range at %s has %d columns; it needs two, '
                      'name then value.'
                      % (cell_name (column, row), len (rows[0])))
  built = []
  for i, (name, value) in enumerate (rows):
    if (name['kind'] == 'empty'):
      continue
    if (name['kind'] != 'text'):
      raise ValueError ('%s holds an option name that is not text.'
                        % cell_name (column, row + i))
    if (value['kind'] == 'empty' and not value.get ('na')):
      raise ValueError ('%s names the option "%s" but %s holds no value.'
                        % (cell_name (column, row + i), name['value'],
                           cell_name (column + 1, row + i)))
    built.append ({'type': 'string', 'value': name['value']})
    built.append (pair_value (value, cell_name (column + 1, row + i),
                              resolve))
  return built


def pair_value (cell, where, resolve):
  """The argument for the value CELL of a pair, found at WHERE.  A value
  holding a "data" key becomes that range, which is how a vector option comes
  from a sheet; a date or time goes as a one-cell range to keep its kind."""
  if (cell.get ('na')):
    # A one-cell range holding only a missing value arrives as NaN
    return range_arg ([[{'kind': 'empty'}]])
  kind, value = cell['kind'], cell.get ('value')
  if (kind == 'text' and value.startswith (MESSAGE_PREFIX)):
    raise ValueError (value[len (MESSAGE_PREFIX):])
  if (kind == 'text' and value.startswith (KEY_PREFIX)):
    mode, column, row, rows = key_range (value, resolve)
    if (mode != 'data'):
      raise ValueError ('%s holds a "pairs" range; an option value takes a '
                        '"data" range.' % where)
    return range_arg (rows)
  if (kind == 'text'):
    return {'type': 'string', 'value': value}
  if (kind == 'number'):
    return {'type': 'number', 'value': value}
  if (kind == 'logical'):
    return {'type': 'logical', 'value': value}
  return range_arg ([[cell]])


def cell_name (column, row):
  """The A1 name of the cell at zero-based COLUMN and ROW."""
  letters = ''
  column += 1
  while (column):
    column, rest = divmod (column - 1, 26)
    letters = chr (ord ('A') + rest) + letters
  return '%s%d' % (letters, row + 1)


def refuse_errors (rows, column, row):
  """A message naming the first error cell in ROWS, or None.  COLUMN and ROW
  place the range's top-left cell on its sheet."""
  for i, cells in enumerate (rows):
    for j, cell in enumerate (cells):
      if (cell['kind'] == 'error'):
        return ('%s holds the error %s.'
                % (cell_name (column + j, row + i), cell['value']))
  return None


def range_mode (mode):
  """The OCTRANGE mode MODE names, in any capitals; "data" when omitted.
  Raises ValueError."""
  if (mode is None or mode == ''):
    return 'data'
  if (isinstance (mode, str) and mode.lower () in MODES):
    return mode.lower ()
  raise ValueError ('mode must be "data" or "pairs".')


def range_key (mode, address, rows):
  """The OCTRANGE key of the range with the absolute name ADDRESS holding
  ROWS of cells, used in MODE."""
  text = json.dumps (rows, sort_keys = True)
  return '%s%s|%s|%s' % (KEY_PREFIX, mode, address,
                         hashlib.sha1 (text.encode ()).hexdigest ())


def key_parts (key):
  """The mode and absolute range name inside an OCTRANGE key, or None when
  KEY is not one."""
  if (not key.startswith (KEY_PREFIX)):
    return None
  mode, _, rest = key[len (KEY_PREFIX):].partition ('|')
  parts = rest.rsplit ('|', 1)
  if (mode not in MODES or len (parts) != 2 or not parts[0]
      or not re.match (r'^[0-9a-f]{40}$', parts[1])):
    return None
  return mode, parts[0]


def remember_range (key, column, row, rows):
  """Keep ROWS, whose top-left cell is at COLUMN and ROW, under KEY."""
  if (key not in _RANGES):
    _RANGES_ORDER.append (key)
  _RANGES[key] = (column, row, rows)
  while (len (_RANGES_ORDER) > _RANGES_LIMIT):
    _RANGES.pop (_RANGES_ORDER.pop (0), None)


def recall_range (key):
  """The column, row and rows kept under KEY, or None."""
  return _RANGES.get (key)


# A label format: numbers show as they would under the default format, and
# text, which in a labelled cell is an OCTRANGE key, shows as the label.
LABEL_NUMBERS = 'General;-General;General;'

LABEL_RE = re.compile (r' \((data|pairs)\)$')


def range_label (key, sheet = None):
  """The label shown in a cell holding the OCTRANGE KEY: the range's address
  and mode, as J1:J4 (data), naming the range's sheet unless it is SHEET."""
  parts = key_parts (key)
  if (parts is None):
    return None
  mode, address = parts
  where, _, cells = address.rpartition ('.')
  where = where.lstrip ('$')
  name = where
  if (len (name) > 1 and name[0] == "'" and name[-1] == "'"):
    name = name[1:-1].replace ("''", "'")
  cells = cells.replace ('$', '')
  if (name != sheet):
    cells = '%s.%s' % (where, cells)
  return '%s (%s)' % (cells, mode)


def label_format (label):
  """The number format code that shows LABEL in place of text.  Every
  character of the label is escaped, so no sheet name can break the code."""
  return LABEL_NUMBERS + ''.join ('\\' + char for char in label)


# Characters that mean something in a format code even unescaped, so that a
# text section holding one of them bare is not a label.
FORMAT_CHARS = '@*_[];"\\'


# The number sections of a label format as Calc may report them: as written,
# or, once the document is reloaded, each behind its condition.
LABEL_SECTIONS = (re.compile (r'^(\[>0\])?General$'),
                  re.compile (r'^(\[<0\])?-General$'),
                  re.compile (r'^General$'))


def format_sections (code):
  """The sections of a number format code, split at the semicolons outside
  quotes and escapes."""
  sections, current, quoted, i = [], [], False, 0
  while (i < len (code)):
    char = code[i]
    if (char == '\\' and not quoted and i + 1 < len (code)):
      current.append (code[i:i + 2])
      i += 2
      continue
    if (char == '"'):
      quoted = not quoted
    if (char == ';' and not quoted):
      sections.append (''.join (current))
      current = []
    else:
      current.append (char)
    i += 1
  sections.append (''.join (current))
  return sections


def label_of_format (code):
  """The label a format code made by label_format shows, or None for any
  other format.  Calc does not keep the code as written: in the session that
  set it the escape before a space is gone, and after a reload the number
  sections carry conditions and the label is quoted.  So the code is read by
  its sections, and the text section decoded: an escaped character or a
  quoted run as itself, bare punctuation and spaces as themselves."""
  sections = format_sections (code)
  if (len (sections) != 4
      or not all (pattern.match (section) for pattern, section
                  in zip (LABEL_SECTIONS, sections))):
    return None
  text = sections[3]
  label = []
  i = 0
  while (i < len (text)):
    char = text[i]
    if (char == '\\'):
      if (i + 1 == len (text)):
        return None
      label.append (text[i + 1])
      i += 2
    elif (char == '"'):
      end = text.find ('"', i + 1)
      if (end < 0):
        return None
      label.append (text[i + 1:end])
      i = end + 1
    elif (char.isalnum () or char in FORMAT_CHARS):
      return None
    else:
      label.append (char)
      i += 1
  label = ''.join (label)
  return label if LABEL_RE.search (label) else None


def iso_date (date):
  """A com.sun.star.util.Date, or anything with Year, Month and Day, written
  YYYY-MM-DD."""
  return '%04d-%02d-%02d' % (date.Year, date.Month, date.Day)


def sandbox_problem ():
  """Why no sandboxed Octave can run on this machine, or None."""
  if (not sys.platform.startswith ('linux')):
    return ('Octave for LibreOffice Calc runs on Linux only, where Octave is '
            'sandboxed.')
  if (not octave ()):
    return 'no octave-cli on PATH.'
  if (not shutil.which ('bwrap')):
    return 'no sandbox: bwrap is not installed (package bubblewrap).'
  if (not shutil.which ('prlimit')):
    return 'no sandbox: prlimit is not installed (package util-linux).'
  return None


def user_manager ():
  """True when a systemd user manager can start a server."""
  runtime = os.environ.get ('XDG_RUNTIME_DIR')
  return bool (shutil.which ('systemd-run') and runtime
               and os.path.exists (os.path.join (runtime, 'systemd',
                                                 'private')))


def server_environment (settings):
  """What a server's launch environment holds for SETTINGS: its folders,
  packages, budgets and deadline."""
  return {'DEVTOOLS_SANDBOX_FOLDERS': os.pathsep.join (settings['folders']),
          'DEVTOOLS_SANDBOX_PACKAGES': ','.join (settings['packages']),
          'DEVTOOLS_SANDBOX_MEMORY': str (settings['memory']),
          'DEVTOOLS_SANDBOX_TMP': str (settings['tmp']),
          'DEVTOOLS_EVAL_SECONDS': str (settings['seconds'])}


def launch_command (binary, settings, unit = None, inherited = None):
  """The command that starts a server running BINARY.  With a UNIT name it
  goes through systemd-run, carrying INHERITED and the settings as its
  environment: the user's service manager then starts the server, outside any
  AppArmor profile confining the office, whose user namespace denial stops
  bwrap even in complain mode.  Without one it is the plain launch."""
  command = [binary, '-q', '--no-init-file', '--eval', LAUNCH]
  if (unit is None):
    return command
  env = dict (inherited or {})
  env.update (server_environment (settings))
  return (['systemd-run', '--user', '--pipe', '--quiet', '--collect',
           '--unit=' + unit]
          + ['--setenv=%s=%s' % item for item in sorted (env.items ())]
          + ['--'] + command)


def sandbox_confirmed (result):
  """True when the initialize RESULT of a server reports its sandbox."""
  meta = (result or {}).get ('_meta') or {}
  return meta.get (SANDBOX_KEY) is True


def cell_value (kind, cell):
  """One element of an octave_call output as a cell holds it: text as text,
  anything else as a number.  A logical value is 1 or 0, a date or duration
  its serial number, NaN a NaN carrying #N/A's code, which Calc shows as
  #N/A, and Inf and -Inf themselves, which Calc shows as #NUM!."""
  if (kind == 'cell'):
    if (cell['kind'] == 'empty'):
      return ''
    return cell_value (cell['kind'], cell['value'])
  if (kind == 'text'):
    return cell
  if (kind == 'logical'):
    return 1.0 if cell else 0.0
  if (cell is None):
    return coded_nan (ERROR_NOT_AVAILABLE)
  # float reads "Inf" and "-Inf" as they come
  return float (cell)


def coded_nan (code):
  """A quiet NaN carrying CODE in its low 32 bits, which is how Calc stores an
  error inside a number and so shows that error."""
  return struct.unpack ('<d', struct.pack ('<Q', 0x7FF8000000000000 | code))[0]


def output_rows (output):
  """The rows of cell values for one octave_call OUTPUT, whose cells come row
  by row.  An empty output is one empty cell."""
  rows, cols = output['rows'], output['cols']
  if (rows == 0 or cols == 0):
    return (('',),)
  values = [cell_value (output['kind'], cell) for cell in output['cells']]
  return tuple (tuple (values[r * cols:(r + 1) * cols]) for r in range (rows))


class Server:
  """One sandboxed devtools.mcpEval process, spoken to over its pipes one
  request at a time.  It starts on its first call, and again on the call
  after it has died or been stopped.

  SETTINGS holds 'folders' and 'packages', lists, and 'memory', 'tmp' and
  'seconds', numbers: the budgets in gigabytes and the deadline."""

  # Numbers the systemd units of the servers this process starts
  started = 0

  def __init__ (self, settings):
    self.settings = settings
    self.process = None
    self.unit = None
    self.errors = None
    self.buffer = b''
    self.next_id = 0
    self.lock = threading.Lock ()

  def call (self, name, args, null_date = NULL_DATE, nargout = 1):
    """The outputs of NAME called on ARGS, as octave_call returns them.
    Raises RuntimeError holding a message fit for a cell."""
    with self.lock:
      if (self.process is None or self.process.poll () is not None):
        self._start ()
      reply = self._request ('tools/call', {
        'name': 'octave_call',
        'arguments': {'function': name, 'args': args, 'nargout': nargout,
                      'nullDate': null_date}},
        self.settings['seconds'] + GRACE_SECONDS)
    if ('error' in reply):
      raise RuntimeError (reply['error'].get ('message', 'the call failed.'))
    result = reply.get ('result') or {}
    content = result.get ('structuredContent') or {}
    if (result.get ('isError')):
      raise RuntimeError (content.get ('error') or 'the call failed.')
    return content['outputs']

  def stop (self):
    """End the process, if one is running.  Closing its input is how the
    server is asked to exit; one that does not is killed."""
    if (self.process is not None):
      try:
        self.process.stdin.close ()
      except Exception:
        pass
      try:
        self.process.wait (timeout = 2)
      except subprocess.TimeoutExpired:
        self.process.kill ()
        self.process.wait ()
        # Killing systemd-run leaves the server it started running
        if (self.unit is not None):
          subprocess.run (['systemctl', '--user', 'stop', self.unit],
                          capture_output = True, timeout = 30)
      self.process.stdout.close ()
      self.process = None
      self.unit = None
    if (self.errors is not None):
      self.errors.close ()
      self.errors = None

  def _start (self):
    problem = sandbox_problem ()
    if (problem):
      raise RuntimeError (problem)
    self.stop ()
    if (user_manager ()):
      Server.started += 1
      self.unit = 'octave-calc-%d-%d' % (os.getpid (), Server.started)
      inherited = {name: os.environ[name] for name in PASSED
                   if name in os.environ}
      command = launch_command (octave (), self.settings, self.unit,
                                inherited)
      env = None
    else:
      command = launch_command (octave (), self.settings)
      env = dict (os.environ)
      env.update (server_environment (self.settings))
    # A file rather than a pipe, which nothing reads until it is needed and
    # which therefore can never fill and stall the server
    self.errors = tempfile.TemporaryFile ()
    self.buffer = b''
    self.process = subprocess.Popen (command, stdin = subprocess.PIPE,
                                     stdout = subprocess.PIPE,
                                     stderr = self.errors, env = env)
    reply = self._request ('initialize', {
      'protocolVersion': PROTOCOL_VERSION, 'capabilities': {},
      'clientInfo': {'name': 'octave-calc', 'version': '0.1.0'}},
      START_SECONDS)
    if (not sandbox_confirmed (reply.get ('result'))):
      self.stop ()
      raise RuntimeError ('the Octave server did not report a sandbox, so '
                          'nothing was evaluated.')
    self._send ({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

  def _send (self, message):
    try:
      self.process.stdin.write ((json.dumps (message) + '\n').encode ())
      self.process.stdin.flush ()
    except OSError:
      raise RuntimeError (self._died ())

  def _request (self, method, params, seconds):
    self.next_id += 1
    self._send ({'jsonrpc': '2.0', 'id': self.next_id, 'method': method,
                 'params': params})
    deadline = time.monotonic () + seconds
    while (True):
      reply = json.loads (self._read_line (deadline, seconds))
      if (reply.get ('id') == self.next_id):
        return reply

  def _read_line (self, deadline, seconds):
    out = self.process.stdout.fileno ()
    while (b'\n' not in self.buffer):
      left = deadline - time.monotonic ()
      if (left <= 0):
        self.stop ()
        raise RuntimeError ('Octave did not answer within %g seconds and was '
                            'stopped; the next call starts it again.'
                            % seconds)
      ready, _, _ = select.select ([out], [], [], left)
      if (ready):
        chunk = os.read (out, 65536)
        if (not chunk):
          raise RuntimeError (self._died ())
        self.buffer += chunk
    line, self.buffer = self.buffer.split (b'\n', 1)
    return line.decode ()

  def _died (self):
    """Why the server stopped, from what it wrote to standard error: Octave's
    last error message, not the call stack printed after it."""
    said = ''
    if (self.errors is not None):
      self.errors.seek (0)
      text = self.errors.read ().decode (errors = 'replace')
      lines = [line.strip () for line in text.splitlines () if line.strip ()]
      messages = [line[len ('error: '):] for line in lines
                  if line.startswith ('error: ')
                  and line != 'error: called from']
      said = messages[-1] if messages else (lines[-1] if lines else '')
    self.stop ()
    if (said):
      return 'the Octave server stopped: %s' % said
    return 'the Octave server stopped.'


# One server per role, 'cell' and 'workbench', since a formula blocks Calc and
# a workbench analysis may run for minutes: each has its own deadline.
_SERVERS = {}
_SERVERS_LOCK = threading.Lock ()


def server (role, settings):
  """The Server for ROLE.  One whose settings have changed is stopped and
  replaced."""
  with _SERVERS_LOCK:
    found = _SERVERS.get (role)
    if (found is None or found.settings != settings):
      if (found is not None):
        found.stop ()
      found = Server (settings)
      _SERVERS[role] = found
    return found


def stop_servers ():
  """Stop every server."""
  with _SERVERS_LOCK:
    for found in _SERVERS.values ():
      found.stop ()
    _SERVERS.clear ()


atexit.register (stop_servers)


def call (name, args, null_date = NULL_DATE, runner = None):
  """What a cell asks for: a matrix, always, or one row holding a message.
  ARGS are octave_call arguments and RUNNER the Server that runs them.

  Errors come back as text rather than as an error value, because the message
  is the useful part and #VALUE! is not."""
  try:
    if (not isinstance (name, str) or not NAME_RE.match (name)):
      return ((MESSAGE_PREFIX + '"%s" is not a function name.' % name,),)
    key = json.dumps ([name, args, null_date, runner.settings],
                      sort_keys = True)
    if (key in _CACHE):
      return _CACHE[key]
    value = output_rows (runner.call (name, args, null_date)[0])
    _CACHE[key] = value
    _CACHE_ORDER.append (key)
    while (len (_CACHE_ORDER) > _CACHE_LIMIT):
      _CACHE.pop (_CACHE_ORDER.pop (0), None)
    return value
  except Exception as err:
    return ((MESSAGE_PREFIX + str (err),),)


def clear ():
  """Forget every memoised result and every kept range."""
  _CACHE.clear ()
  del _CACHE_ORDER[:]
  _RANGES.clear ()
  del _RANGES_ORDER[:]
