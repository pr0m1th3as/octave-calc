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
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile

OCTAVE_CANDIDATES = ('octave-cli', 'octave')

# A bare function name, or a namespaced or static-method one: mean, geom.area,
# ClassName.method.  Anything else never reaches the interpreter.
NAME_RE = re.compile (r'^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)*$')

OCTAVE_FLAGS = ('-q', '--no-init-file', '--no-site-file', '--no-history')

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
  recalculates."""
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
    if (value['kind'] == 'empty'):
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


def iso_date (date):
  """A com.sun.star.util.Date, or anything with Year, Month and Day, written
  YYYY-MM-DD."""
  return '%04d-%02d-%02d' % (date.Year, date.Month, date.Day)


def script (in_path, out_path, err_path, name):
  """The code the interpreter runs.  Every path here is one we made, and the
  only value taken from the user is NAME, which matched NAME_RE.  The
  arguments are read out of the file as data and never appear in this text,
  and devtools decodes them exactly as its octave_call does."""
  return (
    "try\n"
    "  pkg load devtools\n"
    "  __oc_in__ = jsondecode (fileread ('%s'));\n"
    "  [__oc_args__, __oc_msg__] = devtools.__callDecode__ (__oc_in__.args, "
    "__oc_in__.nullDate, ! isempty (which ('datetime')));\n"
    "  if (! isempty (__oc_msg__))\n"
    "    error ('%%s', __oc_msg__);\n"
    "  endif\n"
    "  __oc_r__ = %s (__oc_args__{:});\n"
    "  __oc_out__ = struct ('class', class (__oc_r__), "
    "'size', size (__oc_r__), 'data', __oc_r__);\n"
    "  __oc_fid__ = fopen ('%s', 'w');\n"
    "  fwrite (__oc_fid__, jsonencode (__oc_out__));\n"
    "  fclose (__oc_fid__);\n"
    "catch __oc_err__\n"
    "  __oc_fid__ = fopen ('%s', 'w');\n"
    "  fwrite (__oc_fid__, __oc_err__.message);\n"
    "  fclose (__oc_fid__);\n"
    "end\n" % (in_path, name, out_path, err_path))


def reshape (result):
  """Normalise what Octave returned into rows."""
  klass, size, data = result['class'], result['size'], result['data']
  if (klass == 'char'):
    return ((data if isinstance (data, str) else '',),)
  if (not isinstance (data, list)):
    return ((data,),)
  if (data and isinstance (data[0], list)):
    return tuple (tuple (row) for row in data)
  # A flat list is a vector, and jsonencode does not say which way it runs.
  rows = (size + [1, 1])[0]
  if (rows == 1):
    return (tuple (data),)
  return tuple ((value,) for value in data)


def run (name, args, null_date = NULL_DATE, timeout = 600):
  """One cold interpreter, synchronously.  ARGS are octave_call arguments.
  Returns rows, or raises."""
  folder = tempfile.mkdtemp (prefix = 'octave-calc-')
  in_path = os.path.join (folder, 'in.json')
  out_path = os.path.join (folder, 'out.json')
  err_path = os.path.join (folder, 'err.txt')
  with open (in_path, 'w') as fid:
    json.dump ({'args': args, 'nullDate': null_date}, fid)
  subprocess.run (list ((octave (),) + OCTAVE_FLAGS)
                  + ['--eval', script (in_path, out_path, err_path, name)],
                  capture_output = True, text = True, timeout = timeout)
  if (os.path.exists (err_path)):
    with open (err_path) as fid:
      raise RuntimeError (fid.read ().strip ().splitlines ()[0])
  if (not os.path.exists (out_path)):
    raise RuntimeError ('%s produced no result.' % name)
  with open (out_path) as fid:
    return reshape (json.load (fid))


def call (name, args, null_date = NULL_DATE):
  """What a cell asks for: a matrix, always, or one row holding a message.
  ARGS are octave_call arguments.

  Errors come back as text rather than as an error value, because the message
  is the useful part and #VALUE! is not."""
  try:
    if (not isinstance (name, str) or not NAME_RE.match (name)):
      return (('octave-calc: "%s" is not a function name.' % name,),)
    if (not octave ()):
      return (('octave-calc: no Octave interpreter on PATH.',),)
    key = json.dumps ([name, args, null_date], sort_keys = True)
    if (key in _CACHE):
      return _CACHE[key]
    value = run (name, args, null_date)
    _CACHE[key] = value
    _CACHE_ORDER.append (key)
    while (len (_CACHE_ORDER) > _CACHE_LIMIT):
      _CACHE.pop (_CACHE_ORDER.pop (0), None)
    return value
  except Exception as err:
    return (('octave-calc: %s' % err,),)


def clear ():
  """Forget every memoised result and every kept range."""
  _CACHE.clear ()
  del _CACHE_ORDER[:]
  _RANGES.clear ()
  del _RANGES_ORDER[:]
