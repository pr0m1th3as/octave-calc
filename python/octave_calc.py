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

"""Octave for LibreOffice Calc: the menu-driven workbench.

Four entry points, invoked from Tools > Macros > Organize Macros > Python
until they move into the extension behind Tools > Octave.

  check_environment  reports whether Octave is reachable and which version.
  run_selection      runs an Octave function over a range and writes what it
                     returns back into the sheet.
  clear_cache        forgets memoised results.
  diagnose           reports on every link in the chain, to a file and a box.

This file holds the office and nothing else.  Running Octave lives in
octave_core, which the Add-In component shares, so the part that can be wrong
is tested from a plain Python prompt and the part that needs LibreOffice holds
no logic worth testing.

Why a thread, and why this is not the cell function: a blocking handler
freezes Calc whatever language it is written in, so the handler returns
at once and results come back through AsyncCallback on the main thread. The
document is never touched from the worker. A formula cannot do any of that,
which is why the cell function is an Add-In and lives elsewhere.
"""

import os
import sys
import threading
import time

import uno
import unohelper
from com.sun.star.awt import XActionListener, XCallback
from com.sun.star.sheet import XRangeSelectionListener

# The script provider does not guarantee this directory is importable, and a
# failure here would take every entry point in this file with it, which is the
# hardest kind of fault to read from a spreadsheet.
try:
  import octave_core
  import octave_settings
except ImportError:
  sys.path.insert (0, os.path.dirname (os.path.abspath (__file__)))
  import octave_core
  import octave_settings

# One run at a time.  A second would fight the first for the output range.
_busy = threading.Lock ()


## Plumbing.

class _Callback (unohelper.Base, XCallback):
  """Runs a zero-argument function on the main thread."""

  def __init__ (self, fn):
    self.fn = fn

  def notify (self, unused):
    self.fn ()


def _ctx ():
  return XSCRIPTCONTEXT.getComponentContext ()


def _create (service):
  ctx = _ctx ()
  return ctx.getServiceManager ().createInstanceWithContext (service, ctx)


def _post (fn):
  """Hand fn to the main thread.  Never touch the document from a worker."""
  _create ('com.sun.star.awt.AsyncCallback').addCallback (
    _Callback (fn), 'octave-calc')


def _window ():
  return XSCRIPTCONTEXT.getDocument ().CurrentController.Frame.ContainerWindow


def _message (title, text, kind = 'INFOBOX'):
  box = _create ('com.sun.star.awt.Toolkit').createMessageBox (
    _window (), uno.Enum ('com.sun.star.awt.MessageBoxType', kind), 1,
    title, text)
  box.execute ()
  box.dispose ()


class _Pick (unohelper.Base, XActionListener):
  """The Select button.  Ends the dialog with a distinguishable answer."""

  def __init__ (self, dialog, state):
    self.dialog, self.state = dialog, state

  def actionPerformed (self, unused):
    self.state['action'] = 'pick'
    self.dialog.endExecute ()

  def disposing (self, unused):
    pass


def _ask_form (title, fields):
  """A small dialog, one labelled field per entry in FIELDS, which is a list
  of (key, label, default).  Returns (action, {key: text}) where action is
  'ok', 'cancel' or 'pick'."""
  dialog = _create ('com.sun.star.awt.UnoControlDialog')
  model = _create ('com.sun.star.awt.UnoControlDialogModel')
  model.Width, model.Title = 230, title
  y = 6
  for key, label_text, default in fields:
    label = model.createInstance ('com.sun.star.awt.UnoControlFixedTextModel')
    label.PositionX, label.PositionY = 6, y
    label.Width, label.Height, label.MultiLine = 218, 20, True
    label.Label = label_text
    model.insertByName (key + '_label', label)
    edit = model.createInstance ('com.sun.star.awt.UnoControlEditModel')
    edit.PositionX, edit.PositionY = 6, y + 22
    edit.Width, edit.Height, edit.Text = 218, 14, default
    model.insertByName (key, edit)
    y += 42

  buttons = (('pick', 'Select...', 'STANDARD', 6),
             ('ok', 'OK', 'OK', 122),
             ('cancel', 'Cancel', 'CANCEL', 174))
  for key, label_text, kind, x in buttons:
    button = model.createInstance ('com.sun.star.awt.UnoControlButtonModel')
    button.PositionX, button.PositionY = x, y + 2
    button.Width, button.Height, button.Label = 52, 16, label_text
    button.PushButtonType = uno.Enum ('com.sun.star.awt.PushButtonType', kind)
    model.insertByName (key, button)
  model.Height = y + 24

  dialog.setModel (model)
  dialog.createPeer (_create ('com.sun.star.awt.Toolkit'), None)
  state = {'action': 'cancel'}
  dialog.getControl ('pick').addActionListener (_Pick (dialog, state))
  accepted = dialog.execute ()
  answers = dict ((key, dialog.getControl (key).getModel ().Text.strip ())
                  for key, unused_label, unused_default in fields)
  dialog.dispose ()
  if (state['action'] == 'pick'):
    return 'pick', answers
  return ('ok' if accepted == 1 else 'cancel'), answers


def _property (name, value):
  item = uno.createUnoStruct ('com.sun.star.beans.PropertyValue')
  item.Name, item.Value = name, value
  return item


class _RangePick (unohelper.Base, XRangeSelectionListener):
  """Reopens the dialog once the user has dragged out a range."""

  def __init__ (self, controller, answers):
    self.controller, self.answers = controller, answers

  def _reopen (self, reference):
    self.controller.removeRangeSelectionListener (self)
    answers = dict (self.answers)
    if (reference):
      answers['range'] = _plain (reference)
    _post (lambda: _prompt (answers))

  def done (self, event):
    self._reopen (event.RangeDescriptor)

  def aborted (self, unused):
    self._reopen (None)

  def disposing (self, unused):
    pass


def _plain (reference):
  """$Sheet1.$A$1:$B$10 reads as Sheet1.A1:B10.  The dollars are noise, and
  they are what a person editing the field by hand gets wrong."""
  return reference.replace ('$', '')


## The selection, and what comes back.

def _selected_range ():
  """The selected range as a UNO range, or None if the selection is not one."""
  selection = XSCRIPTCONTEXT.getDocument ().getCurrentSelection ()
  if (selection is None):
    return None
  if (selection.supportsService ('com.sun.star.sheet.SheetCellRange')):
    return selection
  if (selection.supportsService ('com.sun.star.sheet.SheetCellRanges')
      and selection.Count == 1):
    return selection.getByIndex (0)
  return None


def _resolve_range (text):
  """A range typed into the dialog, back into a UNO range, or None.  Accepts
  $Sheet1.$A$1:$B$10 as the selection reports it, Sheet1.A1:B10, and a bare
  A1:B10, which means the active sheet."""
  document = XSCRIPTCONTEXT.getDocument ()
  reference = text.replace ('$', '').strip ()
  if (not reference):
    return None
  if ('.' in reference):
    sheet_name, reference = reference.rsplit ('.', 1)
    sheet_name = sheet_name.strip ("'")
    if (not document.Sheets.hasByName (sheet_name)):
      return None
    sheet = document.Sheets.getByName (sheet_name)
  else:
    sheet = document.CurrentController.ActiveSheet
  try:
    return sheet.getCellRangeByName (reference)
  except Exception:
    return None


def _placement (address, rows, width):
  """Where the result goes, decided by its shape against the selection's.

  The principle is alignment.  A result with as many ROWS as the selection has
  one value per input row, so it belongs beside it, each output row against
  the row it came from; that is what a dim-2 reduction gives, and also what an
  elementwise transform of a single column gives.  A result with as many
  COLUMNS instead has one value per input column and belongs underneath them.
  A result matching neither goes below.  Nothing is left between the two:
  the result starts in the next row or the next column.

  Rows are tested first.  Testing columns first put a sorted 10-by-1 column
  under its source rather than beside it, which is the wrong place, and no
  case has yet been found where rows-first is the wrong one."""
  in_rows = address.EndRow - address.StartRow + 1
  in_columns = address.EndColumn - address.StartColumn + 1
  if (len (rows) == in_rows):
    return address.EndColumn + 1, address.StartRow
  if (width == in_columns):
    return address.StartColumn, address.EndRow + 1
  return address.StartColumn, address.EndRow + 1


def _parse_args (text):
  """Split a comma-separated argument list into octave_call arguments.  A
  token that reads as a number becomes one; anything else is a string, quoted
  or not, so both  2, omitnan  and  2, 'omitnan'  work.  Quoting forces a
  string, which is how a literal "2" is passed."""
  if (not text.strip ()):
    return []
  tokens, token, quoted, quote = [], '', False, None
  for char in text:
    if (quote):
      if (char == quote):
        quote = None
      else:
        token += char
    elif (char in '"\''):
      quote, quoted = char, True
    elif (char == ','):
      tokens.append ((token, quoted))
      token, quoted = '', False
    else:
      token += char
  tokens.append ((token, quoted))

  args = []
  for raw, was_quoted in tokens:
    item = raw.strip ()
    if (item == ''):
      continue
    if (was_quoted):
      args.append ({'type': 'string', 'value': item})
      continue
    try:
      args.append ({'type': 'number', 'value': float (item)})
    except ValueError:
      args.append ({'type': 'string', 'value': item})
  return args


def _call_text (name, source, args):
  """How the call reads to a human.  Provenance, not code to be run."""
  shown = [source]
  for arg in args:
    shown.append ('"%s"' % arg['value'] if arg['type'] == 'string'
                  else _number (arg['value']))
  return '%s (%s)' % (name, ', '.join (shown))


def _number (value):
  return str (int (value)) if float (value).is_integer () else str (value)


## Entry points.

def check_environment ():
  """Report whether the two things this needs are in place."""
  problem = octave_core.sandbox_problem ()
  if (problem):
    _message ('Octave for LibreOffice Calc', problem, 'ERRORBOX')
    return
  binary = octave_core.octave ()
  if (not binary):
    _message ('Octave for LibreOffice Calc',
              'No Octave interpreter was found on PATH.\n\n'
              'Install GNU Octave, or add it to PATH, and try again.\n'
              'Looked for: '
              + ', '.join (octave_core.OCTAVE_CANDIDATES) + '.',
              'ERRORBOX')
    return
  try:
    version = octave_core.octave_version (binary)
  except Exception as err:
    _message ('Octave for LibreOffice Calc',
              'Found %s but could not run it.\n\n%s' % (binary, err),
              'ERRORBOX')
    return
  _message ('Octave for LibreOffice Calc',
            'Octave %s\n%s\n\nReady.' % (version, binary))


def run_selection ():
  """Run an Octave function over a range and write back what it returns.
  Returns at once; the work happens on a thread."""
  problem = octave_core.sandbox_problem ()
  if (problem):
    _message ('Octave for LibreOffice Calc', problem, 'ERRORBOX')
    return
  cell_range = _selected_range ()
  _prompt ({'name': 'mean',
            'range': _plain (cell_range.AbsoluteName) if cell_range else '',
            'args': ''})


def _prompt (defaults):
  """Ask, then either run, or hand over to the mouse picker and come back."""
  action, answers = _ask_form ('Octave for LibreOffice Calc', (
    ('name', 'Function to run.  The range is its first argument.',
     defaults['name']),
    ('range', 'Range holding the data.  Select... picks it with the mouse.',
     defaults['range']),
    ('args', 'Further arguments, comma separated.  Example:  2, omitnan',
     defaults['args'])))

  if (action == 'cancel'):
    return
  if (action == 'pick'):
    _start_pick (answers)
    return
  _launch (answers)


def _start_pick (answers):
  """Hand the sheet to the user to drag a range out.  Asynchronous: the
  listener reopens the dialog when they are done or have given up."""
  controller = XSCRIPTCONTEXT.getDocument ().CurrentController
  try:
    controller.addRangeSelectionListener (_RangePick (controller, answers))
    controller.startRangeSelection ((
      _property ('InitialValue', answers['range']),
      _property ('Title', 'Range holding the data'),
      _property ('CloseOnMouseRelease', True)))
  except Exception as err:
    _message ('Octave for LibreOffice Calc',
              'This view cannot pick a range with the mouse:\n\n%s\n\n'
              'Type the reference instead.' % err, 'ERRORBOX')
    _post (lambda: _prompt (answers))


def _launch (answers):
  """Validate, then run on a worker thread."""
  cell_range = _resolve_range (answers['range'])
  if (cell_range is None):
    _message ('Octave for LibreOffice Calc',
              '"%s" is not a range in this document.\n\n'
              'Write it as Sheet1.A1:B10, or A1:B10 for the active sheet.'
              % answers['range'], 'ERRORBOX')
    return

  name = answers['name']
  if (not octave_core.NAME_RE.match (name)):
    _message ('Octave for LibreOffice Calc',
              '"%s" is not a function name.\n\n'
              'A name only: mean, geom.area, ClassName.method.  This runs a '
              'named function, never arbitrary code.' % name, 'ERRORBOX')
    return
  try:
    args = _parse_args (answers['args'])
  except Exception as err:
    _message ('Octave for LibreOffice Calc',
              'Could not read the argument list:\n\n%s' % err, 'ERRORBOX')
    return

  if (not _busy.acquire (blocking = False)):
    _message ('Octave for LibreOffice Calc',
              'A run is already under way.  Wait for it to finish.')
    return

  data = octave_core.plain_range (cell_range.getDataArray ())
  null_date = octave_core.iso_date (XSCRIPTCONTEXT.getDocument ().NullDate)
  address = cell_range.RangeAddress
  sheet = XSCRIPTCONTEXT.getDocument ().Sheets.getByIndex (address.Sheet)
  call = _call_text (name, _plain (cell_range.AbsoluteName), args)
  try:
    settings = octave_settings.read (XSCRIPTCONTEXT.getComponentContext (),
                                     'workbench')
  except Exception as err:
    _busy.release ()
    _message ('Octave for LibreOffice Calc',
              'Could not read the extension settings:\n\n%s' % err,
              'ERRORBOX')
    return

  def work ():
    try:
      started = time.time ()
      outputs = octave_core.server ('workbench', settings).call (
        name, [data] + args, null_date)
      rows = octave_core.output_rows (outputs[0])
      elapsed = time.time () - started
      _post (lambda: _land (sheet, address, rows, call, elapsed))
    except Exception as err:
      detail = str (err)
      _post (lambda: _message ('Octave for LibreOffice Calc',
                               '%s raised:\n\n%s' % (name, detail),
                               'ERRORBOX'))
    finally:
      _busy.release ()

  threading.Thread (target = work, daemon = True).start ()


def _land (sheet, address, rows, call, elapsed):
  """Main thread: write the result where its shape says it belongs, and mark
  the whole block as one thing rather than leaving loose numbers behind."""
  if (not rows or not rows[0]):
    _message ('Octave for LibreOffice Calc', '%s returned nothing.' % call)
    return
  width = max (len (r) for r in rows)
  padded = tuple (tuple (r) + ('',) * (width - len (r)) for r in rows)
  column, row = _placement (address, padded, width)
  target = sheet.getCellRangeByPosition (column, row,
                                         column + width - 1,
                                         row + len (padded) - 1)
  target.setDataArray (padded)

  # Three marks, and each answers a different question.  The annotation says
  # what produced these numbers, and sits on one cell because that is Calc's
  # own convention for a note.  The outline says where the block begins and
  # ends.  The name makes the block a thing the document knows about, so it
  # can be picked from the Name Box and reached from a formula.
  _annotate (sheet, column, row, call)
  _outline (target)
  _name_result (sheet, target, call)


def _annotate (sheet, column, row, text):
  """Put TEXT in the cell's annotation, replacing one already there.  The
  author and timestamp are the office's own and are not ours to set."""
  address = uno.createUnoStruct ('com.sun.star.table.CellAddress')
  address.Sheet = sheet.RangeAddress.Sheet
  address.Column, address.Row = column, row
  annotations = sheet.Annotations
  for index in range (annotations.Count - 1, -1, -1):
    position = annotations.getByIndex (index).Position
    if (position.Column == column and position.Row == row):
      annotations.removeByIndex (index)
  annotations.insertNew (address, text)


def _outline (target):
  """A thin box around the block.  Inner borders are left alone, so this does
  not disturb formatting the user put there."""
  line = uno.createUnoStruct ('com.sun.star.table.BorderLine2')
  line.LineStyle = 0
  line.LineWidth = 18
  line.Color = 0x808080
  border = uno.createUnoStruct ('com.sun.star.table.TableBorder2')
  for side in ('Top', 'Bottom', 'Left', 'Right'):
    setattr (border, side + 'Line', line)
    setattr (border, 'Is' + side + 'LineValid', True)
  border.IsHorizontalLineValid = False
  border.IsVerticalLineValid = False
  target.TableBorder2 = border


def _name_result (sheet, target, call):
  """Give the block a name in the document.  A re-run over the same cells
  reuses its name rather than piling up octave_mean_1, _2, _3."""
  document = XSCRIPTCONTEXT.getDocument ()
  names = document.NamedRanges
  content = target.AbsoluteName
  for name in tuple (names.ElementNames):
    if (name.startswith ('octave_')
        and names.getByName (name).Content == content):
      names.removeByName (name)

  stem = 'octave_' + re.sub (r'[^A-Za-z0-9_]', '_', call.split (' ')[0])
  candidate, index = stem, 1
  while (names.hasByName (candidate)):
    index += 1
    candidate = '%s_%d' % (stem, index)

  position = uno.createUnoStruct ('com.sun.star.table.CellAddress')
  position.Sheet = sheet.RangeAddress.Sheet
  position.Column = target.RangeAddress.StartColumn
  position.Row = target.RangeAddress.StartRow
  try:
    names.addNewByName (candidate, content, position, 0)
  except Exception:
    pass


def diagnose ():
  """Write a report on every link in the cell-function chain to
  /tmp/octave-calc-diagnose.txt.  Each check stands alone, so one failure
  does not hide the others."""
  report = []

  def check (label, fn):
    try:
      report.append ('%-22s %s' % (label, fn ()))
    except Exception as err:
      report.append ('%-22s FAILED: %s: %s'
                     % (label, type (err).__name__, err))

  check ('octave binary', lambda: octave_core.octave () or 'NOT FOUND')
  check ('octave version', lambda:
         octave_core.octave_version (octave_core.octave ()))
  check ('document url', lambda:
         XSCRIPTCONTEXT.getDocument ().getURL () or 'UNSAVED')

  def extension ():
    provider = _create (
      'com.sun.star.deployment.ExtensionManager')
    for package in provider.getDeployedExtensions ('user', None, None):
      if (package.getIdentifier ().Value == 'io.github.pr0m1th3as.octavecalc'):
        return 'installed, version %s' % package.getVersion ()
    return 'NOT INSTALLED'
  check ('extension', extension)

  check ('add-in service', lambda:
         'instantiates' if _create ('org.octavecalc.Octave') else 'returned None')

  def cell_function ():
    access = _create ('com.sun.star.sheet.FunctionAccess')
    return repr (access.callFunction (
      'OCTAVE', ('mean', ((3.0, 2.0, 8.0), (5.0, 4.0, 6.0)))))
  check ('=OCTAVE through Calc', cell_function)

  check ('octave_core.call', lambda:
         repr (octave_core.call ('mean', [octave_core.plain_range (
           ((3.0, 2.0, 8.0), (5.0, 4.0, 6.0)))], runner = octave_core.server (
             'cell', octave_settings.read (
               XSCRIPTCONTEXT.getComponentContext (), 'cell')))))

  text = '\n'.join (report)
  with open ('/tmp/octave-calc-diagnose.txt', 'w') as fid:
    fid.write (text + '\n')
  _message ('Octave for LibreOffice Calc', text)


def clear_cache ():
  """Forget every memoised result, so the next call runs Octave again."""
  octave_core.clear ()
  _message ('Octave for LibreOffice Calc',
            'Cached results cleared.\n\nThe next call runs Octave again; '
            'press Ctrl+Shift+F9 to force a recalculation.')


g_exportedScripts = (check_environment, run_selection, clear_cache, diagnose)
