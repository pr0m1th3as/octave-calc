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
import octave_layout
import octave_settings
import octave_stats

IMPLEMENTATION = 'org.octavecalc.StatisticsMenuImpl'
SERVICE = 'com.sun.star.frame.ProtocolHandler'
PROTOCOL = 'org.octavecalc.statistics:'

# The analysis functions, mounted in the sandbox beside the user's folders.
FOLDER = os.path.join (HERE, 'octave')

# The menu entry's own title, before an analysis is chosen.
MENU_TITLE = 'Statistics with GNU Octave'

# The layout buttons, in the order of octave_stats.BY.  Where each of them
# goes is octave_layout's business, an analysis being drawn only the layouts
# it takes.
RADIO_NAMES = [name for unused, name, label in octave_layout.RADIOS]

# Option rows the dialog holds ready, since a control cannot be added once
# it is open.  One option is drawn in one row, however tall it stands.
OPTION_SLOTS = octave_stats.OPTION_SLOTS

# What the mouse is told it is picking, by field.
PICK_TITLE = dict (
  [('input', 'Input range'), ('output', 'Results to')]
  + [('input%d' % (n + 1), 'Input %d' % (n + 1)) for n in range (4)]
  + [('output%d' % (n + 1), 'Output %d' % (n + 1)) for n in range (3)])

# A note beside an option's name is italic.  A FixedText is one font
# throughout, so the name and the note are two controls, not one label.
ITALIC = uno.Enum ('com.sun.star.awt.FontSlant', 'ITALIC')

# Rows of a list drawn open rather than dropped down, which scrolls past
# them.  A dropped-open list is a window the theme draws wider than the box
# it came from and with a frame of its own, which an open one is not.
LIST_ROWS = 4

# The units a control is created in against the pixels it is moved in.  A
# model takes its place from the dialog only when the peer is made, so an
# analysis laid out after that is moved control by control.
APPFONT = uno.getConstantByName ('com.sun.star.util.MeasureUnit.APPFONT')
POSSIZE = uno.getConstantByName ('com.sun.star.awt.PosSize.POSSIZE')

# One analysis at a time.  A second would fight the first for the sheet.
_busy = threading.Lock ()

# The first-run report is said once a session, as the sandbox warning is.
_CHECKED = []


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
    self.first_run ()
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

  def first_run (self):
    """Say once a session what is missing or limited here, before anything
    has been asked for.  Every cause is reported otherwise on the first
    failed run, one at a time and only after a dialog has been filled in.
    Starting the server is what that first run would pay anyway."""
    if (_CHECKED):
      return
    _CHECKED.append (True)
    try:
      found = octave_core.first_run (self.settings ())
    except Exception:
      # A check that cannot run says nothing; the analysis reports it
      return
    if (found):
      self.message ('\n\n'.join (found), 'WARNINGBOX')

  def settings (self):
    """The server settings an analysis runs with: the user's own folders
    and the extension's beside them, and the statistics package the
    analyses need added to whatever the user asked for."""
    settings = octave_settings.read (self.ctx, 'workbench')
    settings['folders'] = settings['folders'] + [FOLDER]
    if (octave_stats.PACKAGE not in settings['packages']):
      settings['packages'] = settings['packages'] + [octave_stats.PACKAGE]
    return settings

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
    answers.

    Every control of the right side is made here, since none can be added
    once the dialog is open, and octave_layout puts each chosen analysis's
    own back where that analysis needs it.  What is made below is therefore
    a starting place and not a layout."""
    model = self.create ('com.sun.star.awt.UnoControlDialogModel')
    model.Title = MENU_TITLE
    model.Width, model.Height = 420, 400
    order, made = [0], []

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
      made.append (name)

    add ('FixedText', 'category_label', 6, 8, 80, 10, Label = 'Category:')
    add ('ListBox', 'category', 6, 19, 190,
         octave_layout.list_height (LIST_ROWS),
         StringItemList = octave_stats.category_names ())
    add ('FixedText', 'category_detail', 6, 63, 190, 20, MultiLine = True)
    add ('FixedText', 'analysis_label', 6, 87, 80, 10, Label = 'Analysis:')
    add ('ListBox', 'analysis', 6, 98, 190, 60)
    add ('FixedText', 'detail', 6, 162, 190, 208, MultiLine = True)
    # Custom analysis alone: the folders and the functions stand where the
    # analysis list and the passage stand, since the category has no
    # analyses of ours to list
    add ('FixedText', 'folders_label', 6, 87, 190, 10, Label = 'Folders:')
    add ('ListBox', 'folders', 6, 98, 190,
         octave_layout.list_height (LIST_ROWS), MultiSelection = True)
    add ('Button', 'folder_browse', 6, 145, 60, 14, Label = 'Browse...')
    add ('Button', 'folder_drop', 70, 145, 60, 14, Label = 'Remove')
    add ('FixedText', 'function_label', 6, 165, 190, 10, Label = 'Function:')
    add ('ComboBox', 'function', 6, 176, 130, 14, Dropdown = True,
         HelpText = 'The functions of the folders picked out above, or of '
                    'all of them where none is picked out.  A name may be '
                    'typed instead, and, where the sandbox is running, it '
                    'may be any core or package function.')
    add ('Button', 'function_add', 140, 176, 56, 14, Label = 'Add')
    add ('FixedText', 'customs_label', 6, 196, 190, 10,
         Label = 'Available custom analyses:')
    add ('ListBox', 'customs', 6, 207, 190, 120)
    add ('Button', 'custom_drop', 6, 331, 60, 14, Label = 'Remove')
    left = len (made)
    # The right side.  Every hint wraps and is given the height its own
    # words need, so that none of them is cut off; one line for all of them
    # is what halved the p-value hint of the rank tests.
    add ('FixedText', 'input_label', 206, 8, 80, 10, Label = 'Input range:')
    add ('Edit', 'input', 206, 19, 140, 14, Text = answers['input'])
    add ('Button', 'input_pick', 350, 19, 64, 14,
         Label = octave_layout.PICK)
    add ('FixedText', 'input_hint', 206, 35, 208, 10, MultiLine = True)
    add ('FixedText', 'by_label', 206, 49, 80, 10)
    # One group of radio buttons, since their tab indices follow each other
    for name in RADIO_NAMES:
      add ('RadioButton', name, 206, 60, 95, 12)
    add ('FixedText', 'by_hint', 206, 90, 208, 30, MultiLine = True)
    # Said above the results range by an analysis the range may size
    add ('FixedText', 'output_intro', 206, 120, 208, 30, MultiLine = True)
    add ('FixedText', 'output_label', 206, 150, 80, 10)
    add ('Edit', 'output', 206, 161, 140, 14, Text = answers['output'])
    add ('Button', 'output_pick', 350, 161, 64, 14,
         Label = octave_layout.PICK)
    add ('FixedText', 'output_hint', 206, 177, 208, 10, MultiLine = True)
    # The size of the draw: the results range where it holds more than one
    # cell, and the two fields where it holds one
    add ('FixedText', 'size_text', 206, 191, 208, 10)
    add ('FixedText', 'rows_label', 206, 191, 26, 10)
    add ('Edit', 'rows_draw', 234, 189, 40, 12)
    add ('FixedText', 'cols_label', 284, 191, 40, 10)
    add ('Edit', 'cols_draw', 326, 189, 40, 12)
    add ('FixedText', 'size_hint', 206, 203, 208, 10, MultiLine = True)
    add ('FixedText', 'seed_label', 206, 217, 26, 10)
    add ('Edit', 'seed', 234, 215, 60, 12)
    add ('FixedText', 'seed_hint', 206, 229, 208, 20, MultiLine = True)
    add ('FixedText', 'options_label', 206, 251, 208, 10, FontWeight = BOLD)
    # Custom analysis draws its own right side: two headed groups, a range
    # button on every slot, and no hint under each, which the option rows
    # have no room for
    add ('FixedText', 'custom_intro', 206, 8, 208, 40, MultiLine = True)
    add ('FixedText', 'in_head', 206, 52, 208, 10, FontWeight = BOLD)
    for place in range (octave_stats.CUSTOM_SLOTS):
      add ('FixedText', 'in%d_label' % place, 206, 66 + 18 * place, 42, 10)
      add ('Edit', 'in%d_text' % place, 250, 66 + 18 * place, 96, 12)
      add ('Button', 'in%d_pick' % place, 350, 65 + 18 * place, 64, 14,
           Label = octave_layout.PICK)
    add ('FixedText', 'pairs_label', 206, 142, 42, 10)
    add ('Edit', 'pairs_text', 250, 140, 164, 12)
    add ('FixedText', 'pairs_hint', 206, 156, 208, 10, MultiLine = True)
    add ('FixedText', 'out_head', 206, 176, 208, 10, FontWeight = BOLD)
    for place in range (octave_stats.CUSTOM_OUTPUTS):
      add ('FixedText', 'out%d_label' % place, 206, 190 + 18 * place, 42, 10)
      add ('Edit', 'out%d_text' % place, 250, 190 + 18 * place, 96, 12)
      add ('Button', 'out%d_pick' % place, 350, 189 + 18 * place, 64, 14,
           Label = octave_layout.PICK)
    add ('FixedText', 'out_hint', 206, 248, 208, 20, MultiLine = True)
    for slot in range (OPTION_SLOTS):
      top = 264 + 12 * slot
      add ('FixedText', 'option%d_label' % slot, 206, top, 100, 10)
      add ('ListBox', 'option%d_box' % slot, 310, top, 104, 12,
           Dropdown = True)
      add ('ListBox', 'option%d_list' % slot, 310, top, 104,
           octave_layout.list_height (LIST_ROWS))
      # One button above the other, and one group: two radio buttons are
      # grouped by following each other in tab order, so nothing may be
      # added between them
      add ('RadioButton', 'option%d_radio0' % slot, 216, top, 198, 11)
      add ('RadioButton', 'option%d_radio1' % slot, 216, top, 198, 11)
      # Boxes, each on or off by itself, so no two of them are a group
      for box in range (octave_stats.CHECK_BOXES):
        add ('CheckBox', 'option%d_check%d' % (slot, box), 216, top, 198, 11)
      add ('Edit', 'option%d_text' % slot, 310, top, 104, 12)
      add ('FixedText', 'option%d_hint' % slot, 206, top, 208, 10,
           MultiLine = True)
      # A row that carries a note reads "name: (what it is)", the note
      # italic, so it needs a name of its own beside it and a field narrow
      # enough to leave them both room
      add ('FixedText', 'option%d_name' % slot, 206, top, 40, 10)
      add ('FixedText', 'option%d_note' % slot, 246, top, 118, 10,
           FontSlant = ITALIC)
      add ('Edit', 'option%d_value' % slot, 368, top, 46, 12)
    right = made[left:]
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
             'function': answers.get ('function', ''), 'placed': {},
             'stuck': False}
    if (state['function'] not in state['customs']):
      state['function'] = state['customs'][0] if state['customs'] else ''

    def part (name):
      return dialog.getControl (name)

    def pixels (width, height):
      """WIDTH and HEIGHT, in the dialog's units, as pixels."""
      size = uno.createUnoStruct ('com.sun.star.awt.Size')
      size.Width, size.Height = width, height
      grown = dialog.convertSizeToPixel (size, APPFONT)
      return grown.Width, grown.Height

    def movable ():
      """Whether a control can be moved at all: an analysis is laid out in
      the dialog's units and a control is moved in pixels, so a conversion
      that is not there, or comes back empty, leaves every control where it
      was made."""
      try:
        wide, tall = pixels (100, 100)
        return wide > 0 and tall > 0
      except Exception:
        traceback.print_exc ()
        return False

    state['stuck'] = not movable ()

    def move (name, place):
      """Put the control NAME where PLACE says and give it the words it
      carries.  Both the model and the control are set: the model is where
      the control was made, and the control is what moves once the dialog
      is open, the two being read apart from then on."""
      control = part (name)
      shown = control.getModel ()
      if ('label' in place):
        shown.Label = place['label']
      if ('help' in place):
        shown.HelpText = place['help']
      if (state['placed'].get (name) != place):
        state['placed'][name] = place
        shown.PositionX, shown.PositionY = place['x'], place['y']
        shown.Width, shown.Height = place['width'], place['height']
        if (not state['stuck']):
          try:
            left_px, top_px = pixels (place['x'], place['y'])
            wide_px, tall_px = pixels (place['width'], place['height'])
            control.setPosSize (left_px, top_px, wide_px, tall_px, POSSIZE)
          except Exception:
            # Said once: a hundred controls would say it a hundred times
            state['stuck'] = True
            traceback.print_exc ()
      control.setVisible (True)

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

    def drawn (command):
      """The size the results range gives COMMAND, where it is an analysis
      the range may size and the range names more than one cell."""
      if (not command or not octave_stats.ANALYSES[command].get ('sized')):
        return None
      return extent (part ('output').getModel ().Text)

    def fill_option (slot, option):
      """What one option row holds: the value the user left in it, or the
      analysis's own default."""
      value = state['options'].get (option['name'], option['default'])
      if ('note' in option):
        part ('option%d_value' % slot).getModel ().Text = str (value)
        return
      kind = option['kind']
      if (kind == 'checks'):
        held = octave_stats.ticked (option, value)
        for box, (choice, unused) in enumerate (option['choices']):
          part ('option%d_check%d' % (slot, box)).getModel ().State = int (
            choice in held)
        return
      if (kind == 'radios'):
        for button, (choice, unused) in enumerate (option['choices']):
          part ('option%d_radio%d' % (slot, button)).getModel ().State = int (
            choice == value)
        return
      if (kind == 'choice'):
        shown = part ('option%d_%s'
                      % (slot, 'list' if option.get ('rows') else 'box'))
        shown.getModel ().StringItemList = tuple (text for unused, text
                                                  in option['choices'])
        offered = [choice for choice, unused in option['choices']]
        shown.getModel ().SelectedItems = (
          offered.index (value) if value in offered else 0,)
        return
      part ('option%d_text' % slot).getModel ().Text = str (value)

    def fill (command, size):
      """What the laid out controls of COMMAND hold.  SIZE is what the
      results range gives a draw, where it gives one."""
      analysis = octave_stats.ANALYSES[command] if command else None
      if (analysis is None):
        return
      if (size):
        part ('size_text').getModel ().Label = (
          'Size: %d rows by %d columns.' % size)
      if (analysis.get ('custom')):
        for place in range (octave_stats.CUSTOM_SLOTS):
          part ('in%d_text' % place).getModel ().Text = state['options'].get (
            'input%d' % (place + 1), '')
        part ('pairs_text').getModel ().Text = state['options'].get ('pairs',
                                                                     '')
        for place in range (octave_stats.CUSTOM_OUTPUTS):
          part ('out%d_text' % place).getModel ().Text = (
            state['options'].get ('output%d' % (place + 1), ''))
        return
      held = None
      for name, choice in zip (RADIO_NAMES, octave_stats.BY):
        if (choice in analysis['layouts']
            and part (name).getModel ().State):
          held = choice
      if (analysis['layouts'] and held is None):
        for name, choice in zip (RADIO_NAMES, octave_stats.BY):
          part (name).getModel ().State = int (choice
                                               == analysis['layouts'][0])
      if (analysis.get ('sized') and not size):
        for control, name in zip (('rows_draw', 'cols_draw'),
                                  analysis['sized']):
          option = octave_stats.option_named (command, name)
          part (control).getModel ().Text = str (
            state['options'].get (name, option['default']))
      if (analysis.get ('seeded')):
        seed = analysis['seeded']
        part ('seed').getModel ().Text = str (
          state['options'].get (seed,
                                octave_stats.option_named (command,
                                                           seed)['default']))
      for slot, option in enumerate (octave_stats.slotted (command)):
        fill_option (slot, option)

    def lay_out (command, refill = True):
      """The right side, laid out for COMMAND alone: every control it draws
      where its own words put it, and every other one hidden.  REFILL is
      false where only the results range has changed, so that what the user
      has typed survives their picking a range and changing their mind."""
      size = drawn (command)
      laid = octave_layout.plan (command, size is not None)
      for name in right:
        if (name not in laid):
          part (name).setVisible (False)
      for name, place in laid.items ():
        move (name, place)
      if (refill):
        fill (command, size)
      elif (size):
        part ('size_text').getModel ().Label = (
          'Size: %d rows by %d columns.' % size)

    def in_folder (path):
      """The functions the folder PATH holds, by name, in order."""
      try:
        return sorted (name[:-2] for name in os.listdir (path)
                       if name.endswith ('.m') and not name.startswith ('.'))
      except Exception:
        return []

    def picked_folders ():
      """The folders picked out in the list, or every one of them where
      none is picked out."""
      at = part ('folders').getSelectedItemsPos ()
      chosen = [state['folders'][n] for n in at
                if 0 <= n < len (state['folders'])]
      return chosen or state['folders']

    def offer_functions ():
      """The functions of the picked out folders, offered in the box a name
      may also be typed into."""
      found = sorted (set (sum ((in_folder (path)
                                 for path in picked_folders ()), [])))
      part ('function').getModel ().StringItemList = tuple (found)

    def show_custom ():
      """The folders and the analyses made of them, in place of the analysis
      list and the passage, for the one category that has neither."""
      part ('folders').getModel ().StringItemList = tuple (state['folders'])
      part ('customs').getModel ().StringItemList = tuple (state['customs'])
      if (state['customs']):
        held = state['function']
        part ('customs').getModel ().SelectedItems = (
          state['customs'].index (held) if held in state['customs'] else 0,)
      offer_functions ()

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
        show_custom ()

    def drop_folder ():
      """Remove every folder picked out, the list taking more than one."""
      at = set (part ('folders').getSelectedItemsPos ())
      if (not at):
        return
      left_over = [path for n, path in enumerate (state['folders'])
                   if n not in at]
      if (keep ('Folders', left_over)):
        state['folders'] = left_over
        show_custom ()

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
        show_custom ()

    def drop_custom ():
      at = part ('customs').getSelectedItemPos ()
      if (not 0 <= at < len (state['customs'])):
        return
      left_over = [name for n, name in enumerate (state['customs'])
                   if n != at]
      if (keep ('Analyses', left_over)):
        state['customs'] = left_over
        state['function'] = left_over[0] if left_over else ''
        show_custom ()

    def show (command):
      """Everything that follows from the chosen analysis."""
      state['command'] = command
      analysis = octave_stats.ANALYSES[command] if command else None
      own = bool (analysis) and analysis.get ('custom')
      part ('detail').getModel ().Label = (
        analysis['detail'] if analysis else 'No analyses here yet.')
      for name in ('analysis_label', 'analysis', 'detail'):
        part (name).setVisible (not own)
      for name in ('folders_label', 'folders', 'folder_browse', 'folder_drop',
                   'function_label', 'function', 'function_add',
                   'customs_label', 'customs', 'custom_drop'):
        part (name).setVisible (bool (own))
      if (own):
        show_custom ()
      lay_out (command)

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
      _Typed (lambda: lay_out (state['command'], False)))
    part ('folders').addItemListener (_Chosen (offer_functions))
    for name, action in (('folder_browse', browse),
                         ('folder_drop', drop_folder),
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
    # The Custom analysis reads its own slots below and draws no option
    # rows, so the rows hold nothing of it to read
    drawn_options = (octave_stats.slotted (command)
                     if command and not analysis.get ('custom') else ())
    for slot, option in enumerate (drawn_options):
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
    if (analysis and analysis.get ('custom')):
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
      settings = self.settings ()
    except Exception as err:
      self.message ('Could not read the extension settings: %s' % err)
      return

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
