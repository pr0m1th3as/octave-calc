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

"""Data > Statistics with GNU Octave: the menu commands, their dialog, and the
results written into the sheet.

A protocol handler for org.octavecalc.statistics: commands.  Addons.xcu puts
one entry in the Data menu directly below Calc's Statistics, with no submenu,
since a merged entry that opens one takes no icon; the analyses are chosen in
the dialog, which holds the categories and their analyses beside the ranges
and the chosen analysis's options.  Each analysis keeps a command of its own
all the same, so a macro can dispatch it.  An analysis runs one Octave
function from the octave folder beside this file, on a worker thread in its
own sandboxed server with the statistics package loaded, and the cells it
returns are written on the main thread through AsyncCallback, as one undoable
action.

A macro can run a command without the dialog by passing InputRange, ResultsTo
and GroupedBy ("columns", "rows", "labels-data" or "data-labels") as dispatch
arguments; the results then overwrite whatever is in their way.
"""

import os
import sys
import threading
import traceback

import uno
import unohelper

from com.sun.star.awt import (XActionListener, XCallback, XItemListener,
                              XTextListener)
from com.sun.star.awt.FontWeight import BOLD
from com.sun.star.awt.MessageBoxButtons import BUTTONS_OK, BUTTONS_YES_NO
from com.sun.star.awt.MessageBoxResults import YES
from com.sun.star.frame import XDispatch, XDispatchProvider
from com.sun.star.lang import XInitialization, XServiceInfo
from com.sun.star.sheet import XRangeSelectionListener
from com.sun.star.sheet.CellFlags import VALUE, DATETIME, STRING, FORMULA
from com.sun.star.sheet.FormulaResult import ERROR as RESULT_ERROR

HERE = os.path.dirname (os.path.abspath (__file__))
sys.path.insert (0, HERE)
import octave_core
import octave_settings
import octave_stats

IMPLEMENTATION = 'org.octavecalc.StatisticsMenuImpl'
SERVICE = 'com.sun.star.frame.ProtocolHandler'
PROTOCOL = 'org.octavecalc.statistics:'

# The analysis functions, mounted in the sandbox beside the user's folders.
FOLDER = os.path.join (HERE, 'octave')

# The menu entry's own title, before an analysis is chosen.
MENU_TITLE = 'Statistics with GNU Octave'

# The Grouped by choices in the dialog, in the order of octave_stats.BY: their
# control names, places and labels.
RADIOS = (('columns', 206, 100, 'Columns'), ('rows', 306, 100, 'Rows'),
          ('labels_data', 206, 114, 'Labels | Data'),
          ('data_labels', 306, 114, 'Data | Labels'))
RADIO_NAMES = [radio[0] for radio in RADIOS]

# Option rows the dialog holds ready, since a control cannot be added once it
# is open.
OPTION_SLOTS = octave_stats.OPTION_SLOTS

# The size and the seed of an analysis that declares them sit where the
# layout buttons sit, which is free because an analysis that takes its size
# from the results range reads no input range and so offers no layouts.
SIZE_TOP = 90

# Said above the results range, where the range is one of two ways of giving
# the size and neither is visible from the other.
SIZE_INTRO = ('Two ways to set the size of the returned cell range: select '
              'the range itself, or select one cell and set the Rows and '
              'Columns below.')

# Said at the top of the Custom analysis's own side, where the input range
# would be, since nothing else says what a slot may hold.
CUSTOM_INTRO = (
  'Each input holds a range of cells, picked with the button beside it, or '
  'a value typed out: a number, text in quotes, true or false, [], a matrix '
  'such as [1, 2; 3, 4], or a range such as 1:5.  Fill them from the first; '
  'only the filled ones are passed, in order, and the pairs after them.')

# What the mouse is told it is picking, by field.
PICK_TITLE = dict (
  [('input', 'Input range'), ('output', 'Results to')]
  + [('input%d' % (n + 1), 'Input %d' % (n + 1)) for n in range (4)]
  + [('output%d' % (n + 1), 'Output %d' % (n + 1)) for n in range (3)])

# Said under the output slots.
OUTPUT_HINT = (
  'Fill them from the first: the function is asked for as many outputs as '
  'you fill.  A single cell takes an output of any size; a range of cells '
  'must match the size of the output exactly.')

# A note beside an option's name is italic.  A FixedText is one font
# throughout, so the name and the note are two controls, not one label.
ITALIC = uno.Enum ('com.sun.star.awt.FontSlant', 'ITALIC')

# Boxes an option row holds ready for a 'checks' option to tick.
CHECK_BOXES = 3

# A list drawn open rather than dropped down, four rows tall and scrolling
# past them.  A dropped-open list is a window the theme draws wider than the
# box it came from and with a frame of its own, which an open one is not.
LIST_ROWS = 44

# What each layout means, on hovering over its button, by the kind of input
# the analysis reads.
LAYOUT_HELP = {
  'range': {
    'columns': 'One group per column.  A first row of text is read as the '
               'group names.',
    'rows': 'One group per row.  A first column of text is read as the group '
            'names.',
    'labels-data': 'Two columns: the group of each value, then the values.  A '
                   'first row of text is a header and is ignored.',
    'data-labels': 'Two columns: the values, then the group of each.  A first '
                   'row of text is a header and is ignored.'},
  'matched': {
    'columns': 'One measurement per column, a row per subject.  A first row '
               'of text is read as the measurement names.',
    'rows': 'One measurement per row, a column per subject.  A first column '
            'of text is read as the measurement names.',
    'labels-data': '',
    'data-labels': ''},
  'factors': {
    'columns': '',
    'rows': '',
    'labels-data': 'Three columns: the two factors of each value, then the '
                   'values.  A first row of text names the two factors.',
    'data-labels': 'Three columns: the values, then the two factors of each.  '
                   'A first row of text names the two factors.'},
  'sample': {
    'columns': 'One column of values.  A first row of text is read as the '
               'name of the sample.',
    'rows': 'One row of values.  A first column of text is read as the name '
            'of the sample.',
    'labels-data': '',
    'data-labels': ''}}

# What the layout chooser is called and what it says under itself, by the kind
# of input, since matched measurements are not groups and reading one as the
# other answers a different question in silence.
BY_LABEL = {'range': 'Grouped by:', 'matched': 'Measurements in:',
            'factors': 'Factors in:', 'sample': 'Sample in:'}

BY_HINT = {
  'range': 'Columns or Rows: one group each, whose first cell may hold its '
           'name.  Labels: two columns, the values and the group of each '
           'value.',
  'matched': 'Columns or Rows: one measurement each, on the same subjects '
             'in the same order.  A first cell may name it; a subject '
             'missing any is left out.',
  'factors': 'Three columns: the values and the two factors each was '
             'measured under, in either order.  A first row of text names '
             'the two factors.',
  'sample': 'Columns or Rows: one column, or one row, of values, whose first '
            'cell may hold the name of the sample.'}

# One analysis at a time.  A second would fight the first for the sheet.
_busy = threading.Lock ()


class _Callback (unohelper.Base, XCallback):
  """Runs a function of no arguments on the main thread."""

  def __init__ (self, fn):
    self.fn = fn

  def notify (self, unused):
    self.fn ()


class _Select (unohelper.Base, XActionListener):
  """A Select button: ends the dialog, naming the field to pick."""

  def __init__ (self, dialog, state, field):
    self.dialog, self.state, self.field = dialog, state, field

  def actionPerformed (self, unused):
    self.state['action'] = self.field
    self.dialog.endExecute ()

  def disposing (self, unused):
    pass


class _Chosen (unohelper.Base, XItemListener):
  """A list whose selection changes the rest of the dialog.  UNO swallows
  what a listener raises, which would leave the dialog half redrawn, so
  anything that goes wrong is printed instead."""

  def __init__ (self, fn):
    self.fn = fn

  def itemStateChanged (self, unused):
    try:
      self.fn ()
    except Exception:
      traceback.print_exc ()

  def disposing (self, unused):
    pass


class _Pressed (unohelper.Base, XActionListener):
  """A button that does its work and leaves the dialog standing."""

  def __init__ (self, fn):
    self.fn = fn

  def actionPerformed (self, unused):
    try:
      self.fn ()
    except Exception:
      traceback.print_exc ()

  def disposing (self, unused):
    pass


class _Typed (unohelper.Base, XTextListener):
  """A field whose text changes the rest of the dialog."""

  def __init__ (self, fn):
    self.fn = fn

  def textChanged (self, unused):
    try:
      self.fn ()
    except Exception:
      traceback.print_exc ()

  def disposing (self, unused):
    pass


class _Picked (unohelper.Base, XRangeSelectionListener):
  """Reopens the dialog once a range has been picked with the mouse, or the
  picking abandoned."""

  def __init__ (self, analysis, controller, field, answers):
    self.analysis, self.controller = analysis, controller
    self.field, self.answers = field, answers

  def reopen (self, reference):
    self.controller.removeRangeSelectionListener (self)
    answers = dict (self.answers)
    if (reference):
      put (answers, self.field, plain (reference))
    self.analysis.post (lambda: self.analysis.prompt (answers))

  def done (self, event):
    self.reopen (event.RangeDescriptor)

  def aborted (self, unused):
    self.reopen (None)

  def disposing (self, unused):
    pass


# The ranges a Custom analysis picks are options and not answers of their
# own, so a field is read and written by name either way.
def held (answers, field):
  """What the field FIELD holds."""
  if (field in ('input', 'output')):
    return answers.get (field, '')
  return answers['options'].get (field, '')


def put (answers, field, value):
  """Put VALUE in the field FIELD."""
  if (field in ('input', 'output')):
    answers[field] = value
    return
  answers['options'] = dict (answers['options'])
  answers['options'][field] = value


def plain (reference):
  """$Sheet1.$A$1:$B$10 as Sheet1.A1:B10."""
  return reference.replace ('$', '')


def sentence (text):
  """A message body as a sentence of its own."""
  return text[:1].upper () + text[1:]


def prop (name, value):
  item = uno.createUnoStruct ('com.sun.star.beans.PropertyValue')
  item.Name, item.Value = name, value
  return item


def bounds (address):
  return (address.Sheet, address.StartColumn, address.StartRow,
          address.EndColumn, address.EndRow)


class Analysis:
  """One visit to the Statistics menu in the Calc window FRAME, running the
  analysis the user chooses in the dialog, or the one COMMAND names."""

  def __init__ (self, ctx, frame, command):
    self.ctx = ctx
    self.frame = frame
    self.document = frame.getController ().getModel ()
    self.command = command if command in octave_stats.ANALYSES else None

  @property
  def title (self):
    """What the dialog, its messages and the undo entry are called."""
    if (self.command is None):
      return MENU_TITLE
    return octave_stats.ANALYSES[self.command]['title']

  @property
  def function (self):
    return octave_stats.ANALYSES[self.command]['function']

  def settings_list (self, name):
    """The string list the setting NAME holds, or nothing where it cannot be
    read; a dialog that cannot reach the settings still opens."""
    try:
      return octave_settings.listed (self.ctx, name)
    except Exception:
      traceback.print_exc ()
      return []

  def create (self, service):
    return self.ctx.ServiceManager.createInstanceWithContext (service,
                                                              self.ctx)

  def post (self, fn):
    """Hand FN to the main thread.  A worker never touches the document."""
    self.create ('com.sun.star.awt.AsyncCallback').addCallback (
      _Callback (fn), None)

  def message (self, text, kind = 'ERRORBOX', buttons = BUTTONS_OK):
    box = self.create ('com.sun.star.awt.Toolkit').createMessageBox (
      self.frame.getContainerWindow (),
      uno.Enum ('com.sun.star.awt.MessageBoxType', kind), buttons, self.title,
      text)
    try:
      return box.execute ()
    finally:
      box.dispose ()

  def refuse (self, text, answers, interactive):
    """Say why nothing was written, and return to the dialog if there is
    one."""
    self.message (sentence (text))
    if (interactive):
      self.post (lambda: self.prompt (answers))

  def start (self, options):
    problem = octave_core.octave_problem ()
    if (problem):
      self.message (sentence (problem))
      return
    if ('InputRange' in options and self.command):
      self.launch ({'command': self.command,
                    'input': options['InputRange'],
                    'output': options.get ('ResultsTo', ''),
                    'by': options.get ('GroupedBy', 'columns'),
                    'options': octave_stats.option_defaults (self.command)},
                   False)
      return
    command = self.command or octave_stats.first_analysis ()
    self.prompt ({'command': command, 'input': self.selected (), 'output': '',
                  'by': 'columns',
                  'options': octave_stats.option_defaults (command)})

  def selected (self):
    """The selected range, as the default input range, or nothing."""
    selection = self.document.getCurrentSelection ()
    try:
      if (selection.supportsService ('com.sun.star.sheet.SheetCellRange')):
        return plain (selection.AbsoluteName)
    except Exception:
      pass
    return ''

  def prompt (self, answers):
    """Ask, then run, or hand the sheet to the mouse and come back."""
    action, answers = self.ask (answers)
    self.command = answers['command']
    if (action == 'cancel'):
      return
    if (action not in ('ok', 'cancel')):
      self.pick (action, answers)
      return
    if (answers['command'] is None):
      self.refuse ('that category holds no analyses yet.', answers, True)
      return
    self.launch (answers, True)

  def ask (self, answers):
    """The dialog: the categories and their analyses on one side, the ranges
    and the chosen analysis's options on the other.  Returns what ended it,
    'ok', 'cancel', or the field whose Select button was pressed, and the
    answers."""
    model = self.create ('com.sun.star.awt.UnoControlDialogModel')
    model.Title = MENU_TITLE
    model.Width, model.Height = 420, 400
    order = [0]

    def add (kind, name, x, y, width, height, **properties):
      control = model.createInstance ('com.sun.star.awt.UnoControl%sModel'
                                      % kind)
      control.PositionX, control.PositionY = x, y
      control.Width, control.Height = width, height
      control.TabIndex = order[0]
      order[0] += 1
      for key, value in properties.items ():
        setattr (control, key, value)
      model.insertByName (name, control)

    add ('FixedText', 'category_label', 6, 8, 80, 10, Label = 'Category:')
    add ('ListBox', 'category', 6, 19, 190, LIST_ROWS,
         StringItemList = octave_stats.category_names ())
    add ('FixedText', 'category_detail', 6, 63, 190, 20, MultiLine = True)
    add ('FixedText', 'analysis_label', 6, 87, 80, 10, Label = 'Analysis:')
    add ('ListBox', 'analysis', 6, 98, 190, 60)
    add ('FixedText', 'detail', 6, 162, 190, 208, MultiLine = True)
    # Custom analysis alone: the folders and the functions stand where the
    # analysis list and the passage stand, since the category has no
    # analyses of ours to list
    add ('FixedText', 'folders_label', 6, 87, 190, 10, Label = 'Folders:')
    add ('ListBox', 'folders', 6, 98, 190, LIST_ROWS)
    add ('Button', 'folder_browse', 6, 145, 60, 14, Label = 'Browse...')
    add ('Button', 'folder_drop', 70, 145, 60, 14, Label = 'Remove')
    add ('FixedText', 'function_label', 6, 165, 190, 10, Label = 'Function:')
    add ('ComboBox', 'function', 6, 176, 130, 14, Dropdown = True,
         HelpText = 'A function from the chosen folder, or, where the '
                    'sandbox is running, the name of any core or package '
                    'function.')
    add ('Button', 'function_add', 140, 176, 56, 14, Label = 'Add')
    add ('FixedText', 'customs_label', 6, 196, 190, 10,
         Label = 'Available custom analyses:')
    add ('ListBox', 'customs', 6, 207, 190, 120)
    add ('Button', 'custom_drop', 6, 331, 60, 14, Label = 'Remove')
    add ('FixedText', 'input_label', 206, 8, 80, 10, Label = 'Input range:')
    add ('Edit', 'input', 206, 19, 140, 14, Text = answers['input'],
         HelpText = 'The range holding the data, such as Sheet1.A1:C20, or '
                    'A1:C20 on the sheet in front.  Numbers and empty cells, '
                    'with the group names or labels the layout calls for.')
    add ('Button', 'input_pick', 350, 18, 64, 16, Label = 'Select...')
    add ('FixedText', 'input_hint', 206, 35, 208, 10,
         Label = 'The cells holding the data, with their group names if any.')
    # Above the results range, in the space an analysis reading no cells
    # leaves where the input range would be
    add ('FixedText', 'output_intro', 206, 12, 208, 30, MultiLine = True,
         Label = SIZE_INTRO)
    add ('FixedText', 'output_label', 206, 49, 80, 10, Label = 'Results to:')
    add ('Edit', 'output', 206, 60, 140, 14, Text = answers['output'],
         HelpText = 'One cell, the top left of the results.  The results grow '
                    'right and down from it, and you are asked before '
                    'anything is overwritten.')
    add ('Button', 'output_pick', 350, 59, 64, 16, Label = 'Select...')
    add ('FixedText', 'output_hint', 206, 76, 208, 10,
         Label = 'The top left cell the results are written from.')
    add ('FixedText', 'by_label', 206, 88, 80, 10, Label = 'Grouped by:')
    # One group of radio buttons, since their tab indices follow each other
    for (name, x, y, label), choice in zip (RADIOS, octave_stats.BY):
      add ('RadioButton', name, x, y, 95, 12, Label = label,
           State = int (answers['by'] == choice),
           HelpText = LAYOUT_HELP['range'][choice])
    # Three lines: matched measurements and two factors both take more than
    # two to say
    add ('FixedText', 'by_hint', 206, 128, 208, 30, MultiLine = True,
         Label = BY_HINT['range'])
    # The size of the draw: the results range where it holds more than one
    # cell, and the two fields where it holds one
    add ('FixedText', 'size_text', 206, SIZE_TOP + 2, 208, 10)
    add ('FixedText', 'rows_label', 206, SIZE_TOP + 2, 26, 10,
         Label = 'Rows:')
    add ('Edit', 'rows_draw', 234, SIZE_TOP, 40, 12)
    add ('FixedText', 'cols_label', 284, SIZE_TOP + 2, 40, 10,
         Label = 'Columns:')
    add ('Edit', 'cols_draw', 326, SIZE_TOP, 40, 12)
    add ('FixedText', 'size_hint', 206, SIZE_TOP + 15, 208, 10)
    add ('FixedText', 'seed_label', 206, SIZE_TOP + 30, 26, 10,
         Label = 'Seed:')
    add ('Edit', 'seed', 234, SIZE_TOP + 28, 60, 12)
    # Two lines, the seed taking more words to explain than fit on one
    add ('FixedText', 'seed_hint', 206, SIZE_TOP + 43, 208, 20,
         MultiLine = True)
    add ('FixedText', 'options_label', 206, 160, 208, 10, Label = 'Options:',
         FontWeight = BOLD)
    # Custom analysis draws its own right side: two headed groups, a range
    # button on every slot, and no hint under each, which the shared option
    # rows have no room for
    add ('FixedText', 'custom_intro', 206, 8, 208, 40, MultiLine = True,
         Label = CUSTOM_INTRO)
    add ('FixedText', 'in_head', 206, 52, 208, 10, FontWeight = BOLD,
         Label = 'Input Arguments:')
    for place in range (octave_stats.CUSTOM_SLOTS):
      top = 66 + 18 * place
      add ('FixedText', 'in%d_label' % place, 206, top + 2, 52, 10,
           Label = 'Input %d:' % (place + 1))
      add ('Edit', 'in%d_text' % place, 260, top, 112, 12)
      add ('Button', 'in%d_pick' % place, 376, top - 1, 38, 14, Label = '...')
    add ('FixedText', 'pairs_label', 206, 142, 52, 10, Label = 'Pairs:')
    add ('Edit', 'pairs_text', 260, 140, 154, 12)
    add ('FixedText', 'pairs_hint', 206, 156, 208, 10)
    add ('FixedText', 'out_head', 206, 176, 208, 10, FontWeight = BOLD,
         Label = 'Output Arguments:')
    for place in range (octave_stats.CUSTOM_OUTPUTS):
      top = 190 + 18 * place
      add ('FixedText', 'out%d_label' % place, 206, top + 2, 52, 10,
           Label = 'Output %d:' % (place + 1))
      add ('Edit', 'out%d_text' % place, 260, top, 112, 12)
      add ('Button', 'out%d_pick' % place, 376, top - 1, 38, 14, Label = '...')
    add ('FixedText', 'out_hint', 206, 248, 208, 20, MultiLine = True,
         Label = OUTPUT_HINT)
    for slot in range (OPTION_SLOTS):
      top = 168 + 24 * slot
      add ('FixedText', 'option%d_label' % slot, 206, top + 2, 100, 10)
      add ('ListBox', 'option%d_box' % slot, 310, top, 104, 12,
           Dropdown = True)
      add ('ListBox', 'option%d_list' % slot, 310, top, 104, LIST_ROWS)
      # One button above the other, and one group: two radio buttons are
      # grouped by following each other in tab order, so nothing may be
      # added between them.  The hint of the row below carries the text.
      add ('RadioButton', 'option%d_radio0' % slot, 216, top + 12, 198, 11)
      add ('RadioButton', 'option%d_radio1' % slot, 216, top + 24, 198, 11)
      # Boxes, each on or off by itself, so no two of them are a group
      for box in range (CHECK_BOXES):
        add ('CheckBox', 'option%d_check%d' % (slot, box), 216,
             top + 12 + 12 * box, 198, 11)
      add ('Edit', 'option%d_text' % slot, 310, top, 104, 12)
      add ('FixedText', 'option%d_hint' % slot, 206, top + 14, 208, 10)
      # A row that carries a note reads "name: (what it is)", the note
      # italic, so it needs a name of its own beside it and a field narrow
      # enough to leave them both room
      add ('FixedText', 'option%d_name' % slot, 206, top + 2, 40, 10)
      add ('FixedText', 'option%d_note' % slot, 246, top + 2, 118, 10,
           FontSlant = ITALIC)
      add ('Edit', 'option%d_value' % slot, 368, top, 46, 12)
    add ('Button', 'ok', 296, 376, 54, 16, Label = 'OK', DefaultButton = True,
         PushButtonType = uno.Enum ('com.sun.star.awt.PushButtonType', 'OK'))
    add ('Button', 'cancel', 356, 376, 54, 16, Label = 'Cancel',
         PushButtonType = uno.Enum ('com.sun.star.awt.PushButtonType',
                                    'CANCEL'))

    dialog = self.create ('com.sun.star.awt.UnoControlDialog')
    dialog.setModel (model)
    dialog.createPeer (self.create ('com.sun.star.awt.Toolkit'), None)
    state = {'action': 'cancel', 'command': answers['command'],
             'commands': (), 'options': dict (answers['options']),
             'folders': self.settings_list ('Folders'),
             'customs': self.settings_list ('Analyses'),
             'function': answers.get ('function', '')}
    if (state['function'] not in state['customs']):
      state['function'] = state['customs'][0] if state['customs'] else ''

    def part (name):
      return dialog.getControl (name)

    def show_options (command):
      """The option rows the chosen analysis draws in them, and no others: a
      list to choose from, or a field to type in.  Every row is emptied
      before it is filled, so that nothing of the analysis before it is left
      behind where this one declares less."""
      own = bool (command) and octave_stats.ANALYSES[command].get ('custom')
      options = octave_stats.slotted (command) if command and not own else ()
      part ('options_label').setVisible (bool (options))
      if (options):
        part ('options_label').getModel ().Label = octave_stats.heading (
          command)
      # Emptied whole before any of it is filled, since an option may write
      # into the row below its own and the pass must not then undo it
      for slot in range (OPTION_SLOTS):
        for kind in (['label', 'hint', 'box', 'text', 'list', 'name', 'note',
                      'value', 'radio0', 'radio1']
                     + ['check%d' % box for box in range (CHECK_BOXES)]):
          part ('option%d_%s' % (slot, kind)).setVisible (False)
        for kind in ('label', 'hint', 'name', 'note'):
          part ('option%d_%s' % (slot, kind)).getModel ().Label = ''
      for slot, option in zip (octave_stats.slot_places (command) if command
                               else (), options):
        label, hint = (part ('option%d_label' % slot),
                       part ('option%d_hint' % slot))
        box, typed, listed = (part ('option%d_box' % slot),
                              part ('option%d_text' % slot),
                              part ('option%d_list' % slot))
        name, note, value_of = (part ('option%d_name' % slot),
                                part ('option%d_note' % slot),
                                part ('option%d_value' % slot))
        buttons = (part ('option%d_radio0' % slot),
                   part ('option%d_radio1' % slot))
        boxes = tuple (part ('option%d_check%d' % (slot, n))
                       for n in range (CHECK_BOXES))
        for control in (box, typed, listed, value_of):
          control.getModel ().HelpText = option.get ('help', option['hint'])
        value = state['options'].get (option['name'], option['default'])
        # A noted row says what the option is beside its name, so it needs
        # no line under it
        if ('note' in option):
          name.getModel ().Label = option['label']
          note.getModel ().Label = '(%s)' % option['note']
          value_of.getModel ().Text = str (value)
          for control in (name, note, value_of):
            control.setVisible (True)
          continue
        label.getModel ().Label = option['label']
        label.setVisible (True)
        # A stack of boxes, each on or off by itself and none of them a
        # group, ticked in the order the option declares them
        if (option['kind'] == 'checks'):
          held = octave_stats.ticked (option, value)
          for tick, (choice, text) in zip (boxes, option['choices']):
            tick.getModel ().Label = text
            tick.getModel ().State = int (choice in held)
            tick.getModel ().HelpText = option.get ('help', option['hint'])
            tick.setVisible (True)
          under = part ('option%d_hint'
                        % (slot + octave_stats.slots (option) - 1))
          under.getModel ().Label = option['hint']
          under.setVisible (True)
          continue
        # A pair of buttons stands where the hint of its own row would, so
        # the hint goes under them, on the row they take up as well
        if (option['kind'] == 'radios'):
          under = part ('option%d_hint' % (slot + 1))
          under.getModel ().Label = option['hint']
          under.setVisible (True)
          for button, (choice, text) in zip (buttons, option['choices']):
            button.getModel ().Label = text
            button.getModel ().State = int (choice == value)
            button.getModel ().HelpText = option.get ('help', option['hint'])
            button.setVisible (True)
          continue
        hint.getModel ().Label = option['hint']
        hint.setVisible (True)
        if (option['kind'] == 'choice'):
          shown = listed if option.get ('rows') else box
          shown.getModel ().StringItemList = tuple (text for unused, text
                                                    in option['choices'])
          offered = [choice for choice, unused in option['choices']]
          shown.getModel ().SelectedItems = (
            offered.index (value) if value in offered else 0,)
          shown.setVisible (True)
          # The hint of a tall list goes under the rows it covers
          if (option.get ('rows')):
            hint.setVisible (False)
          continue
        typed.getModel ().Text = str (value)
        typed.setVisible (True)

    def extent (text):
      """The results range TEXT holds, as (rows, columns), where it names a
      range of more than one cell; nothing otherwise, a single cell and a
      size of 1 by 1 meaning the same thing."""
      try:
        at = self.resolve (text, 'results range').getRangeAddress ()
      except Exception:
        return None
      size = (at.EndRow - at.StartRow + 1, at.EndColumn - at.StartColumn + 1)
      return size if size[0] * size[1] > 1 else None

    def show_size (command, refill = True):
      """The size of the draw: what the results range gives, or the two
      fields where it gives nothing.  REFILL is false where only the results
      range has changed, so that what the user has typed into the fields
      survives their picking a range and changing their mind."""
      named = (octave_stats.ANALYSES[command].get ('sized') if command
               else None)
      seeded = (octave_stats.ANALYSES[command].get ('seeded') if command
                else None)
      size = extent (part ('output').getModel ().Text) if named else None
      part ('output_intro').setVisible (bool (named))
      part ('size_text').setVisible (size is not None)
      for name in ('rows_label', 'rows_draw', 'cols_label', 'cols_draw'):
        part (name).setVisible (bool (named) and size is None)
      part ('size_hint').setVisible (bool (named))
      for name in ('seed_label', 'seed', 'seed_hint'):
        part (name).setVisible (bool (seeded))
      # A range of more than one cell is not a corner the results grow from
      part ('output_hint').getModel ().Label = (
        'The cell range the results are written into.' if size
        else 'The top left cell the results are written from.')
      if (size):
        part ('size_text').getModel ().Label = (
          'Size: %d rows by %d columns.' % size)
      if (named and refill):
        rows, cols = (octave_stats.option_named (command, name)
                      for name in named)
        part ('size_hint').getModel ().Label = rows['hint']
        for control, option in (('rows_draw', rows), ('cols_draw', cols)):
          part (control).getModel ().Text = str (
            state['options'].get (option['name'], option['default']))
          part (control).getModel ().HelpText = option.get ('help',
                                                           option['hint'])
      if (seeded and refill):
        seed = octave_stats.option_named (command, seeded)
        part ('seed_label').getModel ().Label = seed['label']
        part ('seed_hint').getModel ().Label = seed['hint']
        part ('seed').getModel ().Text = str (
          state['options'].get (seeded, seed['default']))
        part ('seed').getModel ().HelpText = seed.get ('help', seed['hint'])

    def in_folder (path):
      """The functions the folder PATH holds, by name, in order."""
      try:
        return sorted (name[:-2] for name in os.listdir (path)
                       if name.endswith ('.m') and not name.startswith ('.'))
      except Exception:
        return []

    def show_custom (command, refill = True):
      """The folders and the functions, in place of the analysis list and
      the passage, for the one category that has neither."""
      own = bool (command) and octave_stats.ANALYSES[command].get ('custom')
      for name in ('folders_label', 'folders', 'folder_browse', 'folder_drop',
                   'function_label', 'function', 'function_add',
                   'customs_label', 'customs', 'custom_drop'):
        part (name).setVisible (bool (own))
      for name in ('analysis_label', 'analysis', 'detail'):
        part (name).setVisible (not own)
      # Its own right side stands in place of the results range and the
      # option rows, which say nothing it needs
      for name in ('custom_intro', 'in_head', 'pairs_label', 'pairs_text',
                   'pairs_hint', 'out_head', 'out_hint'):
        part (name).setVisible (bool (own))
      for place in range (octave_stats.CUSTOM_SLOTS):
        for kind in ('label', 'text', 'pick'):
          part ('in%d_%s' % (place, kind)).setVisible (bool (own))
      for place in range (octave_stats.CUSTOM_OUTPUTS):
        for kind in ('label', 'text', 'pick'):
          part ('out%d_%s' % (place, kind)).setVisible (bool (own))
      for name in ('output_label', 'output', 'output_pick', 'output_hint'):
        part (name).setVisible (not own)
      if (not own):
        return
      part ('pairs_hint').getModel ().Label = octave_stats.option_named (
        command, 'pairs')['hint']
      for place in range (octave_stats.CUSTOM_SLOTS):
        part ('in%d_text' % place).getModel ().Text = state['options'].get (
          'input%d' % (place + 1), '')
      part ('pairs_text').getModel ().Text = state['options'].get ('pairs', '')
      for place in range (octave_stats.CUSTOM_OUTPUTS):
        part ('out%d_text' % place).getModel ().Text = state['options'].get (
          'output%d' % (place + 1), '')
      if (not refill):
        return
      part ('folders').getModel ().StringItemList = tuple (state['folders'])
      part ('customs').getModel ().StringItemList = tuple (state['customs'])
      if (state['customs']):
        held = state['function']
        part ('customs').getModel ().SelectedItems = (
          state['customs'].index (held) if held in state['customs'] else 0,)
      offer_functions ()

    def offer_functions ():
      """The functions of the chosen folder, or of every folder where none
      is chosen, offered in the box a name may also be typed into."""
      at = part ('folders').getSelectedItemPos ()
      folders = ([state['folders'][at]] if 0 <= at < len (state['folders'])
                 else state['folders'])
      found = sorted (set (sum ((in_folder (path) for path in folders), [])))
      part ('function').getModel ().StringItemList = tuple (found)

    def keep (name, values):
      """Put VALUES in the setting NAME, saying so where it cannot be
      done."""
      try:
        octave_settings.relist (self.ctx, name, values)
        return True
      except Exception as err:
        self.message ('The settings could not be changed: %s' % err)
        return False

    def browse ():
      """Add a folder, starting at the user's own."""
      picker = self.create ('com.sun.star.ui.dialogs.FolderPicker')
      picker.setDisplayDirectory (
        uno.systemPathToFileUrl (os.path.expanduser ('~')))
      if (picker.execute () != 1):
        return
      path = uno.fileUrlToSystemPath (picker.getDirectory ())
      if (path in state['folders']):
        return
      if (keep ('Folders', state['folders'] + [path])):
        state['folders'] = state['folders'] + [path]
        show_custom (state['command'])

    def drop_folder ():
      at = part ('folders').getSelectedItemPos ()
      if (not 0 <= at < len (state['folders'])):
        return
      left = [path for n, path in enumerate (state['folders']) if n != at]
      if (keep ('Folders', left)):
        state['folders'] = left
        show_custom (state['command'])

    def add_function ():
      """Put the named function among the custom analyses."""
      name = part ('function').getModel ().Text.strip ()
      if (not name):
        return
      if (name in state['customs']):
        return
      if (keep ('Analyses', state['customs'] + [name])):
        state['customs'] = state['customs'] + [name]
        state['function'] = name
        show_custom (state['command'])

    def drop_custom ():
      at = part ('customs').getSelectedItemPos ()
      if (not 0 <= at < len (state['customs'])):
        return
      left = [name for n, name in enumerate (state['customs']) if n != at]
      if (keep ('Analyses', left)):
        state['customs'] = left
        state['function'] = left[0] if left else ''
        show_custom (state['command'])

    def show (command):
      """Everything that follows from the chosen analysis."""
      state['command'] = command
      analysis = octave_stats.ANALYSES[command] if command else None
      part ('detail').getModel ().Label = (
        analysis['detail'] if analysis else 'No analyses here yet.')
      # An analysis that reads no cells hides the range and the layouts
      kind = analysis['input'] if analysis else 'none'
      reads = kind != 'none' and bool (analysis)
      for name in ('input_label', 'input', 'input_pick', 'input_hint',
                   'by_label', 'by_hint') + tuple (RADIO_NAMES):
        part (name).setVisible (reads)
      if (reads):
        part ('by_label').getModel ().Label = BY_LABEL[kind]
        part ('by_hint').getModel ().Label = BY_HINT[kind]
        for name, choice in zip (RADIO_NAMES, octave_stats.BY):
          part (name).getModel ().HelpText = LAYOUT_HELP[kind][choice]
      held = None
      for name, choice in zip (RADIO_NAMES, octave_stats.BY):
        offered = bool (analysis) and choice in analysis['layouts']
        part (name).getModel ().Enabled = offered
        if (offered and part (name).getModel ().State):
          held = choice
      # An analysis that reads no cells offers no layout to fall back on
      if (analysis and analysis['layouts'] and held is None):
        for name, choice in zip (RADIO_NAMES, octave_stats.BY):
          part (name).getModel ().State = int (choice == analysis['layouts'][0])
      show_size (command)
      show_custom (command)
      show_options (command)

    def show_category (category, command = None):
      """The analyses of CATEGORY, on COMMAND where it is one of them."""
      part ('category_detail').getModel ().Label = (
        octave_stats.CATEGORIES[category])
      part ('analysis_label').getModel ().Label = (
        octave_stats.list_label (category))
      commands = octave_stats.analyses_of (category)
      state['commands'] = commands
      part ('analysis').getModel ().StringItemList = tuple (
        octave_stats.listed (each) for each in commands)
      if (commands):
        if (command not in commands):
          command = commands[0]
        part ('analysis').getModel ().SelectedItems = (
          commands.index (command),)
      show (command if commands else None)

    def category_chosen ():
      show_category (
        octave_stats.category_names ()[part ('category')
                                       .getSelectedItemPos ()])

    def analysis_chosen ():
      position = part ('analysis').getSelectedItemPos ()
      if (0 <= position < len (state['commands'])):
        show (state['commands'][position])

    opening = answers['command'] or octave_stats.first_analysis ()
    names = octave_stats.category_names ()
    category = (octave_stats.ANALYSES[opening]['category'] if opening
                else names[0])
    part ('category').getModel ().SelectedItems = (names.index (category),)
    show_category (category, opening)
    part ('category').addItemListener (_Chosen (category_chosen))
    part ('analysis').addItemListener (_Chosen (analysis_chosen))
    part ('output').addTextListener (
      _Typed (lambda: show_size (state['command'], False)))
    part ('folders').addItemListener (_Chosen (offer_functions))
    for name, action in (('folder_browse', browse), ('folder_drop', drop_folder),
                         ('function_add', add_function),
                         ('custom_drop', drop_custom)):
      part (name).addActionListener (_Pressed (action))
    for place in range (octave_stats.CUSTOM_SLOTS):
      part ('in%d_pick' % place).addActionListener (
        _Select (dialog, state, 'input%d' % (place + 1)))
    for place in range (octave_stats.CUSTOM_OUTPUTS):
      part ('out%d_pick' % place).addActionListener (
        _Select (dialog, state, 'output%d' % (place + 1)))
    for field in ('input', 'output'):
      part (field + '_pick').addActionListener (_Select (dialog, state, field))
    ended = dialog.execute ()
    by = 'columns'
    for name, choice in zip (RADIO_NAMES, octave_stats.BY):
      if (part (name).getModel ().State):
        by = choice
    command, values = state['command'], dict (state['options'])
    analysis = octave_stats.ANALYSES[command] if command else None
    drawn = (list (zip (octave_stats.slot_places (command),
                        octave_stats.slotted (command))) if command else ())
    for slot, option in drawn:
      if ('note' in option):
        values[option['name']] = (
          part ('option%d_value' % slot).getModel ().Text.strip ())
        continue
      if (option['kind'] == 'checks'):
        values[option['name']] = ' '.join (
          choice for n, (choice, unused) in enumerate (option['choices'])
          if part ('option%d_check%d' % (slot, n)).getModel ().State)
        continue
      if (option['kind'] == 'radios'):
        for button, (choice, unused) in enumerate (option['choices']):
          if (part ('option%d_radio%d' % (slot, button)).getModel ().State):
            values[option['name']] = choice
        continue
      if (option['kind'] == 'choice'):
        shown = 'option%d_list' if option.get ('rows') else 'option%d_box'
        position = part (shown % slot).getSelectedItemPos ()
        if (0 <= position < len (option['choices'])):
          values[option['name']] = option['choices'][position][0]
        continue
      values[option['name']] = (
        part ('option%d_text' % slot).getModel ().Text.strip ())
    if (analysis and analysis.get ('sized')):
      for control, name in zip (('rows_draw', 'cols_draw'), analysis['sized']):
        values[name] = part (control).getModel ().Text.strip ()
    if (analysis and analysis.get ('seeded')):
      values[analysis['seeded']] = part ('seed').getModel ().Text.strip ()
    at = part ('customs').getSelectedItemPos ()
    if (0 <= at < len (state['customs'])):
      state['function'] = state['customs'][at]
    if (command and octave_stats.ANALYSES[command].get ('custom')):
      for place in range (octave_stats.CUSTOM_SLOTS):
        values['input%d' % (place + 1)] = (
          part ('in%d_text' % place).getModel ().Text.strip ())
      values['pairs'] = part ('pairs_text').getModel ().Text.strip ()
      for place in range (octave_stats.CUSTOM_OUTPUTS):
        values['output%d' % (place + 1)] = (
          part ('out%d_text' % place).getModel ().Text.strip ())
    answers = {'command': command,
               'input': part ('input').getModel ().Text.strip (),
               'output': part ('output').getModel ().Text.strip (),
               'by': by, 'options': values,
               'function': state['function']}
    dialog.dispose ()
    if (state['action'] != 'cancel'):
      return state['action'], answers
    return ('ok' if ended == 1 else 'cancel'), answers

  def pick (self, field, answers):
    """Let the user drag out the range for FIELD.  The listener reopens the
    dialog when they are done or have given up."""
    controller = self.document.getCurrentController ()
    listener = _Picked (self, controller, field, answers)
    try:
      controller.addRangeSelectionListener (listener)
      controller.startRangeSelection ((
        prop ('InitialValue', held (answers, field)),
        prop ('Title', PICK_TITLE.get (field, 'Range')),
        prop ('CloseOnMouseRelease', True)))
    except Exception as err:
      controller.removeRangeSelectionListener (listener)
      self.message ('This view cannot pick a range with the mouse: %s\n\n'
                    'Type the reference instead.' % err)
      self.post (lambda: self.prompt (answers))

  def resolve (self, text, what):
    """The range TEXT names: Sheet1.A1:B10, $Sheet1.$A$1:$B$10, or A1:B10 on
    the active sheet.  WHAT names the field in a refusal.  Raises
    ValueError."""
    reference = plain (text).strip ()
    if (not reference):
      raise ValueError ('the %s is empty.' % what)
    if ('.' in reference):
      name, cells = reference.rsplit ('.', 1)
      if (len (name) > 1 and name[0] == "'" and name[-1] == "'"):
        name = name[1:-1].replace ("''", "'")
      if (not self.document.Sheets.hasByName (name)):
        raise ValueError ('the %s "%s" is not a range in this document.'
                          % (what, text))
      sheet = self.document.Sheets.getByName (name)
    else:
      cells = reference
      sheet = self.document.getCurrentController ().getActiveSheet ()
    try:
      return sheet.getCellRangeByName (cells)
    except Exception:
      raise ValueError ('the %s "%s" is not a range in this document.'
                        % (what, text))

  def sized (self, answers, corner):
    """ANSWERS with the size options of an analysis that takes its size from
    the results range replaced by the extent of CORNER.  A single cell leaves
    them as the dialog holds them, so that one cell and a size of 1 by 1 mean
    the same thing.  The block written is taller than the numbers by the
    lines above them, which start at the corner either way."""
    named = octave_stats.ANALYSES[self.command].get ('sized')
    if (not named):
      return answers
    at = corner.getRangeAddress ()
    height = at.EndRow - at.StartRow + 1
    width = at.EndColumn - at.StartColumn + 1
    if (height * width == 1):
      return answers
    answers = dict (answers)
    answers['options'] = dict (answers['options'])
    answers['options'][named[0]] = str (height)
    answers['options'][named[1]] = str (width)
    return answers

  def custom_corners (self, answers):
    """Where each output of a Custom analysis goes, as the cell it is
    written from and the size it must be, which is nothing where a single
    cell lets it be any size.  Raises ValueError."""
    held = answers['options']
    texts = [held.get ('output%d' % (place + 1), '').strip ()
             for place in range (octave_stats.CUSTOM_OUTPUTS)]
    octave_stats.filled (texts, 'output')
    if (not texts[0]):
      raise ValueError ('no output is given; the first says where the '
                        "function's first result is written.")
    corners = []
    for place, text in enumerate (texts):
      if (not text):
        continue
      found = self.resolve (text, 'output %d' % (place + 1))
      at = found.getRangeAddress ()
      size = (at.EndRow - at.StartRow + 1, at.EndColumn - at.StartColumn + 1)
      corners.append ((found, None if size == (1, 1) else size))
    return corners

  def custom_args (self, answers):
    """The arguments of a Custom analysis: what its inputs hold, each read
    as a literal or resolved as a range.  Raises ValueError."""
    if (not answers.get ('function')):
      raise ValueError ('no function is chosen.  Add one on the left, from '
                        'a folder of your own.')
    held = answers['options']

    def resolve (text, what, refusal):
      try:
        found = self.resolve (text, what)
      except ValueError:
        raise ValueError ('%s holds neither a range of this document nor a '
                          'value: %s' % (what, refusal))
      return octave_core.plain_range (found.getDataArray ())

    return octave_stats.custom_args (
      [held.get ('input%d' % (place + 1), '')
       for place in range (octave_stats.CUSTOM_SLOTS)],
      held.get ('pairs', ''), resolve)

  def launch (self, answers, interactive):
    """Check the answers, then run the analysis on a worker thread."""
    self.command = answers['command']
    analysis = octave_stats.ANALYSES[self.command]
    layouts = analysis['layouts']
    by = answers['by'] if answers['by'] in layouts else (layouts or ('',))[0]
    where = None
    try:
      if (analysis.get ('custom')):
        corners = self.custom_corners (answers)
        corner = corners[0][0]
        args = self.custom_args (answers)
      else:
        corner = self.resolve (answers['output'], 'results range')
        corners = [(corner, None)]
        answers = self.sized (answers, corner)
        args = octave_stats.option_args (self.command, answers['options'])
      if (analysis['input'] != 'none'):
        source = self.resolve (answers['input'], 'input range')
        where = source.getRangeAddress ()
        errors = source.queryFormulaCells (RESULT_ERROR).getRangeAddresses ()
        if (errors):
          raise ValueError ('%s holds an error; %s'
                            % (octave_core.cell_name (errors[0].StartColumn,
                                                      errors[0].StartRow),
                               octave_stats.allowed (by, analysis['input'])))
        args = (octave_stats.analysis_args (source.getDataArray (), by,
                                            where.StartColumn, where.StartRow,
                                            analysis['input'])
                + args)
    except ValueError as err:
      self.refuse (str (err), answers, interactive)
      return

    try:
      settings = octave_settings.read (self.ctx, 'workbench')
    except Exception as err:
      self.message ('Could not read the extension settings: %s' % err)
      return
    settings['folders'] = settings['folders'] + [FOLDER]
    if (octave_stats.PACKAGE not in settings['packages']):
      settings['packages'] = settings['packages'] + [octave_stats.PACKAGE]

    if (not _busy.acquire (blocking = False)):
      self.message ('An analysis is already running.  Wait for it to finish.',
                    'INFOBOX')
      return
    function = (answers.get ('function') if analysis.get ('custom')
                else self.function)
    # A function of the user's own folders runs wherever the menu does; any
    # other name is core's or a package's, and reaching one by name needs a
    # sandbox, since the arguments come from the document
    own = (not analysis.get ('custom')
           or any (os.path.exists (os.path.join (folder, function + '.m'))
                   for folder in settings['folders']))
    null_date = octave_core.iso_date (self.document.NullDate)

    def work ():
      try:
        runner = octave_core.server ('statistics', settings)
        if (not own and runner.state != 'active'):
          raise RuntimeError (
            '%s is not in your own folders, and reaching a core or package '
            'function by name needs the sandbox, which is not running here. '
            'Add the folder that holds it instead.' % function)
        outputs = runner.call (function, args, null_date, len (corners))
        tables = [octave_core.output_rows (outputs[n])
                  for n in range (len (corners))]
        placed = [(spot, table, wanted) for (spot, wanted), table
                  in zip (corners, tables)]
        self.post (lambda: self.land (where, placed, answers, interactive))
        # A sandbox that should work and does not is said once a session
        warning = octave_core.failed_warning (runner)
        if (warning):
          self.post (lambda: self.message (warning, 'WARNINGBOX'))
      except Exception as err:
        detail = octave_stats.reason (str (err), function)
        self.post (lambda: self.refuse (detail, answers, interactive))
      finally:
        _busy.release ()

    threading.Thread (target = work, daemon = True).start ()

  def land (self, where, placed, answers, interactive):
    """Main thread: write each table from the cell it was given, now that its
    size is known, as one undoable action, and select the first, as Calc does
    with its own results.  PLACED is the corner, the table and the size the
    corner asks for, which is nothing where it is a single cell.  WHERE is
    the input range's address."""
    blocks = []
    for corner, table, wanted in placed:
      top = corner.getRangeAddress ()
      sheet = self.document.Sheets.getByIndex (top.Sheet)
      height, width = len (table), len (table[0]) if table else 0
      at = plain (corner.AbsoluteName)
      if (wanted is not None and wanted != (height, width)):
        self.refuse ('%s is %d rows by %d columns and the result written '
                     'there is %d by %d; pick a single cell to let it be any '
                     'size.' % (at, wanted[0], wanted[1], height, width),
                     answers, interactive)
        return
      try:
        block = sheet.getCellRangeByPosition (
          top.StartColumn, top.StartRow, top.StartColumn + width - 1,
          top.StartRow + height - 1)
      except Exception:
        self.refuse ('the results, %d rows by %d columns, do not fit on the '
                     'sheet from %s.' % (height, width, at), answers,
                     interactive)
        return
      if (where is not None
          and octave_stats.overlaps (bounds (where),
                                     bounds (block.getRangeAddress ()))):
        self.refuse ('the results, %s, would overwrite the input range.'
                     % plain (block.AbsoluteName), answers, interactive)
        return
      blocks.append ((block, table))
    for first in range (len (blocks)):
      for second in range (first + 1, len (blocks)):
        if (octave_stats.overlaps (
              bounds (blocks[first][0].getRangeAddress ()),
              bounds (blocks[second][0].getRangeAddress ()))):
          self.refuse ('output %d and output %d would be written over each '
                       'other.' % (first + 1, second + 1), answers,
                       interactive)
          return
    if (interactive):
      for block, table in blocks:
        if (block.queryContentCells (
              VALUE | DATETIME | STRING | FORMULA).getRangeAddresses ()):
          if (self.message ('The results range %s is not empty.  Overwrite '
                            'it?' % plain (block.AbsoluteName), 'QUERYBOX',
                            BUTTONS_YES_NO) != YES):
            self.post (lambda: self.prompt (answers))
            return

    # Cell by cell, since Calc's undo of setDataArray restores nothing.  A
    # value set directly cannot be an error, so a missing value is =NA(), and
    # an infinity is its text, as datatypes writes it, since Calc loads a
    # non-finite number from a file as 0.
    undo = self.document.getUndoManager ()
    undo.enterUndoContext (self.title)
    try:
      for block, table in blocks:
        block.clearContents (VALUE | DATETIME | STRING | FORMULA)
        for r, row in enumerate (table):
          for c, value in enumerate (row):
            cell = block.getCellByPosition (c, r)
            if (isinstance (value, str)):
              if (value != ''):
                cell.setString (value)
            elif (value != value):
              cell.setFormula ('=NA()')
            elif (value == float ('inf')):
              cell.setString ('Inf')
            elif (value == float ('-inf')):
              cell.setString ('-Inf')
            else:
              cell.setValue (value)
    finally:
      undo.leaveUndoContext ()
    try:
      self.document.getCurrentController ().select (blocks[0][0])
    except Exception:
      pass


class StatisticsMenu (unohelper.Base, XInitialization, XDispatchProvider,
                      XDispatch, XServiceInfo):

  def __init__ (self, ctx):
    self.ctx = ctx
    self.frame = None

  # XInitialization.  The frame the command was given in.
  def initialize (self, args):
    if (args):
      self.frame = args[0]

  # XDispatchProvider.
  def queryDispatch (self, url, target, flags):
    if (url.Protocol == PROTOCOL
        and (url.Path == 'Menu' or url.Path in octave_stats.ANALYSES)):
      return self
    return None

  def queryDispatches (self, requests):
    return tuple (self.queryDispatch (request.FeatureURL, request.FrameName,
                                      request.SearchFlags)
                  for request in requests)

  # XDispatch.
  def dispatch (self, url, args):
    try:
      Analysis (self.ctx, self.frame, url.Path).start (
        dict ((arg.Name, arg.Value) for arg in (args or ())))
    except Exception:
      # Nothing else reports what a menu command raises
      traceback.print_exc ()

  def addStatusListener (self, listener, url):
    event = uno.createUnoStruct ('com.sun.star.frame.FeatureStateEvent')
    event.FeatureURL, event.IsEnabled, event.Source = url, True, self
    listener.statusChanged (event)

  def removeStatusListener (self, listener, url):
    pass

  # XServiceInfo.
  def getImplementationName (self):
    return IMPLEMENTATION

  def supportsService (self, name):
    return name == SERVICE

  def getSupportedServiceNames (self):
    return (SERVICE,)


g_ImplementationHelper = unohelper.ImplementationHelper ()
g_ImplementationHelper.addImplementation (StatisticsMenu, IMPLEMENTATION,
                                          (SERVICE,))
