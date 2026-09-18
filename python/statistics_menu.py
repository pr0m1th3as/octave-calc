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

from com.sun.star.awt import XActionListener, XCallback, XItemListener
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
RADIOS = (('columns', 206, 102, 'Columns'), ('rows', 306, 102, 'Rows'),
          ('labels_data', 206, 116, 'Labels | Data'),
          ('data_labels', 306, 116, 'Data | Labels'))
RADIO_NAMES = [radio[0] for radio in RADIOS]

# Option rows the dialog holds ready, since a control cannot be added once it
# is open.  An analysis may declare no more options than this.
OPTION_SLOTS = 6

# What each layout means, on hovering over its button.
LAYOUT_HELP = {
  'columns': 'One group per column.  A first row of text is read as the '
             'group names.',
  'rows': 'One group per row.  A first column of text is read as the group '
          'names.',
  'labels-data': 'Two columns: the group of each value, then the values.  A '
                 'first row of text is a header and is ignored.',
  'data-labels': 'Two columns: the values, then the group of each.  A first '
                 'row of text is a header and is ignored.'}

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
  """A list whose selection changes the rest of the dialog."""

  def __init__ (self, fn):
    self.fn = fn

  def itemStateChanged (self, unused):
    self.fn ()

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
      answers[self.field] = plain (reference)
    self.analysis.post (lambda: self.analysis.prompt (answers))

  def done (self, event):
    self.reopen (event.RangeDescriptor)

  def aborted (self, unused):
    self.reopen (None)

  def disposing (self, unused):
    pass


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
    if (action in ('input', 'output')):
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
    model.Width, model.Height = 420, 340
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
    add ('ListBox', 'category', 6, 19, 190, 12, Dropdown = True,
         StringItemList = octave_stats.category_names ())
    add ('FixedText', 'category_detail', 6, 35, 190, 20, MultiLine = True)
    add ('FixedText', 'analysis_label', 6, 60, 80, 10, Label = 'Analysis:')
    add ('ListBox', 'analysis', 6, 71, 190, 60)
    add ('FixedText', 'detail', 6, 135, 190, 175, MultiLine = True)
    add ('FixedText', 'input_label', 206, 8, 80, 10, Label = 'Input range:')
    add ('Edit', 'input', 206, 19, 140, 14, Text = answers['input'],
         HelpText = 'The range holding the data, such as Sheet1.A1:C20, or '
                    'A1:C20 on the sheet in front.  Numbers and empty cells, '
                    'with the group names or labels the layout calls for.')
    add ('Button', 'input_pick', 350, 18, 64, 16, Label = 'Select...')
    add ('FixedText', 'input_hint', 206, 35, 208, 10,
         Label = 'The cells holding the data, with their group names if any.')
    add ('FixedText', 'output_label', 206, 49, 80, 10, Label = 'Results to:')
    add ('Edit', 'output', 206, 60, 140, 14, Text = answers['output'],
         HelpText = 'One cell, the top left of the results.  The results grow '
                    'right and down from it, and you are asked before '
                    'anything is overwritten.')
    add ('Button', 'output_pick', 350, 59, 64, 16, Label = 'Select...')
    add ('FixedText', 'output_hint', 206, 76, 208, 10,
         Label = 'The top left cell the results are written from.')
    add ('FixedText', 'by_label', 206, 90, 80, 10, Label = 'Grouped by:')
    # One group of radio buttons, since their tab indices follow each other
    for (name, x, y, label), choice in zip (RADIOS, octave_stats.BY):
      add ('RadioButton', name, x, y, 95, 12, Label = label,
           State = int (answers['by'] == choice), HelpText = LAYOUT_HELP[choice])
    add ('FixedText', 'by_hint', 206, 132, 208, 20, MultiLine = True,
         Label = 'Columns or Rows: one group each, whose first cell may hold '
                 'its name.  Labels: two columns, the values and the group of '
                 'each value.')
    add ('FixedText', 'options_label', 206, 156, 80, 10, Label = 'Options:')
    for slot in range (OPTION_SLOTS):
      top = 168 + 24 * slot
      add ('FixedText', 'option%d_label' % slot, 206, top + 2, 100, 10)
      add ('ListBox', 'option%d_box' % slot, 310, top, 104, 12, Dropdown = True)
      add ('Edit', 'option%d_text' % slot, 310, top, 104, 12)
      add ('FixedText', 'option%d_hint' % slot, 206, top + 14, 208, 10)
    add ('Button', 'ok', 296, 316, 54, 16, Label = 'OK', DefaultButton = True,
         PushButtonType = uno.Enum ('com.sun.star.awt.PushButtonType', 'OK'))
    add ('Button', 'cancel', 356, 316, 54, 16, Label = 'Cancel',
         PushButtonType = uno.Enum ('com.sun.star.awt.PushButtonType',
                                    'CANCEL'))

    dialog = self.create ('com.sun.star.awt.UnoControlDialog')
    dialog.setModel (model)
    dialog.createPeer (self.create ('com.sun.star.awt.Toolkit'), None)
    state = {'action': 'cancel', 'command': answers['command'],
             'commands': (), 'options': dict (answers['options'])}

    def part (name):
      return dialog.getControl (name)

    def show_options (command):
      """The option rows the chosen analysis declares, and no others: a list
      to choose from, or a field to type a number in."""
      options = octave_stats.ANALYSES[command]['options'] if command else ()
      part ('options_label').setVisible (bool (options))
      for slot in range (OPTION_SLOTS):
        option = options[slot] if slot < len (options) else None
        label, hint = (part ('option%d_label' % slot),
                       part ('option%d_hint' % slot))
        box, typed = (part ('option%d_box' % slot),
                      part ('option%d_text' % slot))
        label.setVisible (option is not None)
        hint.setVisible (option is not None)
        box.setVisible (option is not None and option['kind'] == 'choice')
        typed.setVisible (option is not None and option['kind'] == 'number')
        if (option is None):
          continue
        label.getModel ().Label = option['label']
        hint.getModel ().Label = option['hint']
        for control in (box, typed):
          control.getModel ().HelpText = option.get ('help', option['hint'])
        value = state['options'].get (option['name'], option['default'])
        if (option['kind'] == 'number'):
          typed.getModel ().Text = str (value)
          continue
        box.getModel ().StringItemList = tuple (text for unused, text
                                                in option['choices'])
        offered = [choice for choice, unused in option['choices']]
        box.getModel ().SelectedItems = (
          offered.index (value) if value in offered else 0,)

    def show (command):
      """Everything that follows from the chosen analysis."""
      state['command'] = command
      analysis = octave_stats.ANALYSES[command] if command else None
      part ('detail').getModel ().Label = (
        analysis['detail'] if analysis else 'No analyses here yet.')
      # An analysis that reads no cells hides the range and the layouts
      reads = bool (analysis) and analysis['input'] == 'range'
      for name in ('input_label', 'input', 'input_pick', 'input_hint',
                   'by_label', 'by_hint') + tuple (RADIO_NAMES):
        part (name).setVisible (reads)
      held = None
      for name, choice in zip (RADIO_NAMES, octave_stats.BY):
        offered = bool (analysis) and choice in analysis['layouts']
        part (name).getModel ().Enabled = offered
        if (offered and part (name).getModel ().State):
          held = choice
      if (analysis and held is None):
        for name, choice in zip (RADIO_NAMES, octave_stats.BY):
          part (name).getModel ().State = int (choice == analysis['layouts'][0])
      show_options (command)

    def show_category (category, command = None):
      """The analyses of CATEGORY, on COMMAND where it is one of them."""
      part ('category_detail').getModel ().Label = (
        octave_stats.CATEGORIES[category])
      commands = octave_stats.analyses_of (category)
      state['commands'] = commands
      part ('analysis').getModel ().StringItemList = tuple (
        octave_stats.ANALYSES[each]['title'] for each in commands)
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
    for field in ('input', 'output'):
      part (field + '_pick').addActionListener (_Select (dialog, state, field))
    ended = dialog.execute ()
    by = 'columns'
    for name, choice in zip (RADIO_NAMES, octave_stats.BY):
      if (part (name).getModel ().State):
        by = choice
    command, values = state['command'], dict (state['options'])
    for slot, option in enumerate (
        octave_stats.ANALYSES[command]['options'][:OPTION_SLOTS]
        if command else ()):
      if (option['kind'] == 'number'):
        values[option['name']] = (
          part ('option%d_text' % slot).getModel ().Text.strip ())
        continue
      position = part ('option%d_box' % slot).getSelectedItemPos ()
      if (0 <= position < len (option['choices'])):
        values[option['name']] = option['choices'][position][0]
    answers = {'command': command,
               'input': part ('input').getModel ().Text.strip (),
               'output': part ('output').getModel ().Text.strip (),
               'by': by, 'options': values}
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
        prop ('InitialValue', answers[field]),
        prop ('Title', 'Input range' if field == 'input' else 'Results to'),
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

  def launch (self, answers, interactive):
    """Check the answers, then run the analysis on a worker thread."""
    self.command = answers['command']
    analysis = octave_stats.ANALYSES[self.command]
    layouts = analysis['layouts']
    by = answers['by'] if answers['by'] in layouts else (layouts or ('',))[0]
    where = None
    try:
      corner = self.resolve (answers['output'], 'results range')
      args = octave_stats.option_args (self.command, answers['options'])
      if (analysis['input'] == 'range'):
        source = self.resolve (answers['input'], 'input range')
        where = source.getRangeAddress ()
        errors = source.queryFormulaCells (RESULT_ERROR).getRangeAddresses ()
        if (errors):
          allowed = octave_stats.ALLOWED.get (by,
                                              octave_stats.ALLOWED['columns'])
          raise ValueError ('%s holds an error; %s'
                            % (octave_core.cell_name (errors[0].StartColumn,
                                                      errors[0].StartRow),
                               allowed))
        args = (octave_stats.analysis_args (source.getDataArray (), by,
                                            where.StartColumn, where.StartRow)
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
    function = self.function
    null_date = octave_core.iso_date (self.document.NullDate)

    def work ():
      try:
        runner = octave_core.server ('statistics', settings)
        outputs = runner.call (function, args, null_date)
        table = octave_stats.results (outputs)
        self.post (lambda: self.land (where, corner, table, answers,
                                      interactive))
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

  def land (self, where, corner, table, answers, interactive):
    """Main thread: place TABLE from the cell CORNER now that its size is
    known, write it as one undoable action, and select it, as Calc does with
    its own results.  WHERE is the input range's address."""
    top = corner.getRangeAddress ()
    sheet = self.document.Sheets.getByIndex (top.Sheet)
    height, width = len (table), len (table[0])
    try:
      block = sheet.getCellRangeByPosition (
        top.StartColumn, top.StartRow, top.StartColumn + width - 1,
        top.StartRow + height - 1)
    except Exception:
      self.refuse ('the results, %d rows by %d columns, do not fit on the '
                   'sheet from %s.' % (height, width,
                                       plain (corner.AbsoluteName)),
                   answers, interactive)
      return
    if (where is not None
        and octave_stats.overlaps (bounds (where),
                                   bounds (block.getRangeAddress ()))):
      self.refuse ('the results, %s, would overwrite the input range.'
                   % plain (block.AbsoluteName), answers, interactive)
      return
    if (interactive and block.queryContentCells (
          VALUE | DATETIME | STRING | FORMULA).getRangeAddresses ()):
      if (self.message ('The results range %s is not empty.  Overwrite it?'
                        % plain (block.AbsoluteName), 'QUERYBOX',
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
      self.document.getCurrentController ().select (block)
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
