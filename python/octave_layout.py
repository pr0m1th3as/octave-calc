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

"""The right side of the dialog: where each control of an analysis goes, and
what it says.

One line of hint under every field is what cut the p-value of the rank tests
in half.  How much a field has to say is the field's own business and no two
fields have the same amount, so nothing here is a fixed row: every block is
as tall as the words it holds, each analysis is stacked from the top of the
column, and the analyses that say little are drawn short.

Nothing here knows about LibreOffice beyond its units, and a test lays out
every analysis without it and sees that the last block still ends above the
buttons.  A control keeps the width it was created with and takes its place
from here.
"""

import textwrap

import octave_stats

# The column: where it starts, how wide it is, and the line above OK and
# Cancel that nothing may cross.
LEFT = 206
COLUMN = 208
TOP = 8
BOTTOM = 372

# Characters a line of text holds across the column.  A dialog unit is a
# quarter of the average character, so the column holds about 52 of them;
# this is short of that on purpose, since a line too many only leaves a gap
# where a line too few cuts the words off.
HINT_CHARS = 48

# A line of text, a field, the button that picks a range beside it, a list
# dropped down or a button or a box in a stack, and a row of the layout
# buttons.
LINE = 10
FIELD = 14
BUTTON = 14
BOX = 12
ROW = 14

# A row of a list drawn open, and the frame around it.
LIST_ROW = 10
LIST_EDGE = 4

# Between a control and the hint under it, and between one block and the
# next.
PAD = 2
GAP = 4

# The width of the label beside a field, of the field itself, and of the
# button that picks a range with the mouse, which is the same button
# wherever it stands.
LABEL_WIDTH = 80
FIELD_WIDTH = 140
PICK_LEFT = 350
PICK_WIDTH = 64

# What the button that picks a range says, everywhere it appears.
PICK = 'Select...'

# The layout buttons: the control of each choice and what it is called, two
# to a row, and only the ones the analysis takes.
RADIOS = (('columns', 'columns', 'Columns'), ('rows', 'rows', 'Rows'),
          ('labels-data', 'labels_data', 'Labels | Data'),
          ('data-labels', 'data_labels', 'Data | Labels'))
RADIO_WIDTH = 95
RADIO_STEP = 100

# What the input range holds, by the kind of input the analysis reads.
INPUT_HINT = {
  'range': 'Select the cells holding your data, the group names included '
           'if your sheet has them.',
  'matched': 'Select the cells holding every measurement of every '
             'subject, their names included if your sheet has them.',
  'factors': 'Select the cells holding your values and the two factors '
             'each value was measured under.',
  'sample': 'Select the cells holding your sample, one column or one row '
            'of values.'}

# The same, at length, on hovering over the field.
INPUT_HELP = {
  'range': 'The range holding your data, such as A1:C20 on the sheet in '
           'front, or Sheet1.A1:C20 on another.  It may hold numbers and '
           'empty cells, and the group names where the arrangement you '
           'choose below reads them.',
  'matched': 'The range holding your data, such as A1:C20 on the sheet in '
             'front, or Sheet1.A1:C20 on another.  Each subject is measured '
             'once under every condition, so every row, or every column, '
             'must be the same length.',
  'factors': 'The range holding your data, such as A1:C20 on the sheet '
             'in front, or Sheet1.A1:C20 on another.  Three columns: the '
             'value, and the level of each of the two factors it was '
             'measured under.',
  'sample': 'The range holding your sample, such as A1:A20 on the sheet '
            'in front, or Sheet1.A1:A20 on another.  One column, or one row, '
            'of numbers and empty cells.'}

# What the chooser under the input range is called, and what it says under
# itself, by the kind of input.  Matched measurements are not independent
# groups, and reading one as the other answers a question the user did not
# ask without saying so, which is why the words are not shared.
BY_LABEL = {'range': 'Grouped by:', 'matched': 'Measurements in:',
            'factors': 'Factors in:', 'sample': 'Sample in:'}

BY_HINT = {
  'range': 'How the groups are arranged in the cells you picked.  Hover '
           'a choice to see the shape it expects.',
  'matched': 'Where each measurement sits in the cells you picked.  '
             'Hover a choice to see the shape it expects.',
  'factors': 'Which of the three columns holds the values.  Hover a '
             'choice to see the shape it expects.',
  'sample': 'Whether your sample is a column or a row.  Hover a choice '
            'to see the shape it expects.'}

# What each layout means, on hovering over its button, by the kind of input.
# A layout an analysis does not take is not drawn at all, so the kinds that
# take two carry two.
LAYOUT_HELP = {
  'range': {
    'columns': 'Each group fills a column of its own, one value per cell.  '
               'A first row of text is read as the group names: the control '
               'group in A2:A20 under its name in A1, the treated group in '
               'B2:B20 under its name in B1.',
    'rows': 'Each group fills a row of its own, one value per cell.  A '
            'first column of text is read as the group names: the control '
            'group in B1:T1 beside its name in A1, the treated group in '
            'B2:T2 beside its name in A2.',
    'labels-data': 'Two columns side by side, however many groups there '
                   'are.  The first names the group each value belongs to, '
                   'the second holds the value: control in A2 and 4.1 in '
                   'B2, treated in A3 and 5.8 in B3.  A first row of text '
                   'is read as a heading and ignored.',
    'data-labels': 'The same two columns the other way round, the value '
                   'first and the group it belongs to second: 4.1 in A2 and '
                   'control in B2.  A first row of text is read as a '
                   'heading and ignored.'},
  'matched': {
    'columns': 'Each measurement fills a column of its own and each subject '
               'a row across them, in the same order in every column.  A '
               'first row of text is read as the measurement names: before '
               'in A2:A20 under its name in A1, after in B2:B20 under its '
               'name in B1.  A subject missing any measurement is left out '
               'of all of them.',
    'rows': 'Each measurement fills a row of its own and each subject a '
            'column down them, in the same order in every row.  A first '
            'column of text is read as the measurement names: before in '
            'B1:T1 beside its name in A1, after in B2:T2 beside its name '
            'in A2.  A subject missing any measurement is left out of all '
            'of them.'},
  'factors': {
    'labels-data': 'Three columns: the two factors first, then the value '
                   'measured under them.  Fertiliser in A2, variety in B2 '
                   'and the yield in C2.  A first row of text is read as '
                   'the names of the two factors.',
    'data-labels': 'The same three columns the other way round, the value '
                   'first and its two factors after it.  The yield in A2, '
                   'fertiliser in B2 and variety in C2.  A first row of '
                   'text is read as the names of the two factors.'},
  'sample': {
    'columns': 'One column of values, such as A2:A20.  A first row of text '
               'is read as the name of the sample, so a heading in A1 names '
               'the results rather than being counted as a value.',
    'rows': 'One row of values, such as B1:T1.  A first column of text is '
            'read as the name of the sample, so a heading in A1 names the '
            'results rather than being counted as a value.'}}

# Where the results go.  An analysis whose size the results range may set
# says so above the field, the two being unable to point at each other.
RESULTS_LABEL = 'Results to:'

RESULTS_HINT = 'The cell the results start from.  They fill right and down '\
               'from it.'


def results_hint (command):
  """What the results field says: where the results start, and how much
  room they take where the analysis knows it.  The analysis carries the
  whole sentence, not the size to drop into one."""
  return octave_stats.ANALYSES[command].get ('results') or RESULTS_HINT

RESULTS_HELP = ('One cell, the top left corner of the results.  They fill '
                'right and down from it, and you are asked before anything '
                'already in the way is overwritten.')

RANGE_HINT = 'The cells the draw fills.  Nothing is written above the '\
             'numbers.'

RANGE_HELP = ('A range of more than one cell is the size of the draw as '
              'well as its place, and the Rows and Columns fields give way '
              'to it.  The numbers fill it exactly: nothing is written '
              'above them or beside them.')

SIZE_INTRO = ('Two ways to set the size of the draw: select the cells it '
              'fills, or select a single cell and set the Rows and Columns '
              'below.')

# The Custom analysis draws its own side: two headed groups of slots, a
# button on each to pick a range with the mouse, and no room for a hint
# under every one of them.
CUSTOM_INTRO = (
  'Each input holds a range of cells, picked with the button beside it, or '
  'a value typed out: a number, text in quotes, true or false, [], a matrix '
  'such as [1, 2; 3, 4], or a range such as 1:5.  What is typed is read and '
  'never run, so a mistake is named here rather than in Octave.')

INPUT_HEAD = 'Input Arguments:'

OUTPUT_HEAD = 'Output Arguments:'

OUTPUT_HINT = (
  'Fill them from the first: the function is asked for as many outputs as '
  'you fill.  A single cell takes an output of any size; a range of cells '
  'must match the size of the output exactly, and is refused with both '
  'sizes when it does not.')

# The width of the label, the field and the pick button of a Custom slot,
# which are narrower than the ones above so that the button is the same.
SLOT_LABEL = 42
SLOT_LEFT = 250
SLOT_WIDTH = 96
PAIRS_WIDTH = 164

# The heading above the option rows, and the rows themselves.  A list is
# drawn OPTION_WIDTH wide unless its entry says how wide it is drawn, and
# stands at the right of the column either way, its label taking the rest
# of the row.

# A row that says what it is beside its own name: the name, the note in
# italics, and a field narrow enough to leave them both room.
NAME_WIDTH = 40
NOTE_LEFT = 246
NOTE_WIDTH = 118
VALUE_LEFT = 368
VALUE_WIDTH = 46


def lines (words, width = HINT_CHARS):
  """How many lines WORDS take across the column."""
  if (not words):
    return 0
  taken = 0
  for paragraph in words.split ('\n'):
    taken += len (textwrap.wrap (paragraph, width)) or 1
  return taken


def words_height (words):
  """How tall a block of WORDS stands."""
  return lines (words) * LINE


def list_height (rows):
  """How tall a list drawn open of ROWS rows stands."""
  return rows * LIST_ROW + LIST_EDGE


def option_height (option):
  """How tall OPTION stands, the hint under it included."""
  if ('note' in option):
    return BOX
  return option_body (option) + under (option['hint'])


def option_body (option):
  """How tall what OPTION draws stands, before the hint under it."""
  kind = option['kind']
  if (kind in ('radios', 'checks')):
    return LINE + PAD + BOX * len (option['choices'])
  if (option.get ('rows')):
    return list_height (option['rows'])
  return BOX


OPTION_LABEL_WIDTH = 100
OPTION_WIDTH = 104
CHOICE_INDENT = 10


def choice_width (option):
  """How wide the list of OPTION is drawn: what its entry says, or a
  field's width where it says nothing."""
  return option.get ('width', OPTION_WIDTH)


def under (words):
  """How much room the hint WORDS take under the control they belong to."""
  return PAD + words_height (words) if words else 0


class _Column:
  """The blocks of the right side, stacked from the top."""

  def __init__ (self):
    self.laid, self.top = {}, TOP

  def put (self, name, x, width, height, **words):
    """NAME at the top of the column, without moving down past it."""
    self.laid[name] = dict (words, x = x, y = self.top, width = width,
                            height = height)

  def down (self, height):
    self.top += height

  def block (self, name, x, width, height, **words):
    """NAME at the top of the column, and the column past it."""
    self.put (name, x, width, height, **words)
    self.down (height)

  def hint (self, name, words, help_text = ''):
    """The hint WORDS under the control above them, as many lines as they
    need, and nothing at all where there are none."""
    if (not words):
      return
    self.down (PAD)
    self.block (name, LEFT, COLUMN, words_height (words), label = words,
                help = help_text or words)

  def gap (self):
    self.top += GAP


def plan (command, by_range = False):
  """Where every control of the right side goes for the analysis COMMAND,
  as its name against a place: x, y, width and height, with the words it
  carries and the tooltip where it has one.  A control the analysis does not
  draw is not in the plan at all.

  BY_RANGE is true where the results range names more than one cell, which
  is one of the two ways a generator is told the size of its draw."""
  column = _Column ()
  if (not command):
    return column.laid
  analysis = octave_stats.ANALYSES[command]
  if (analysis.get ('custom')):
    return custom_plan (column, command)
  kind = analysis['input']
  if (kind != 'none'):
    column.block ('input_label', LEFT, LABEL_WIDTH, LINE,
                  label = 'Input range:')
    column.put ('input', LEFT, FIELD_WIDTH, FIELD, help = INPUT_HELP[kind])
    column.block ('input_pick', PICK_LEFT, PICK_WIDTH, BUTTON, label = PICK,
                  help = 'Pick the input range with the mouse.')
    column.hint ('input_hint', INPUT_HINT[kind])
    column.gap ()
    column.block ('by_label', LEFT, LABEL_WIDTH, LINE, label = BY_LABEL[kind])
    offered = [radio for radio in RADIOS if radio[0] in analysis['layouts']]
    for first in range (0, len (offered), 2):
      for place, (choice, name, label) in enumerate (offered[first:first + 2]):
        column.put (name, LEFT + RADIO_STEP * place, RADIO_WIDTH, BOX,
                    label = label, help = LAYOUT_HELP[kind][choice])
      column.down (ROW)
    column.hint ('by_hint', BY_HINT[kind])
    column.gap ()
  if (analysis.get ('sized')):
    column.block ('output_intro', LEFT, COLUMN, words_height (SIZE_INTRO),
                  label = SIZE_INTRO)
    column.gap ()
  column.block ('output_label', LEFT, LABEL_WIDTH, LINE,
                label = RESULTS_LABEL)
  column.put ('output', LEFT, FIELD_WIDTH, FIELD,
              help = RANGE_HELP if by_range else RESULTS_HELP)
  column.block ('output_pick', PICK_LEFT, PICK_WIDTH, BUTTON, label = PICK,
                help = 'Pick the results range with the mouse.')
  column.hint ('output_hint',
               RANGE_HINT if by_range else results_hint (command))
  column.gap ()
  if (analysis.get ('sized')):
    size_plan (column, command, by_range)
  if (analysis.get ('seeded')):
    seed_plan (column, command)
  options_plan (column, command)
  return column.laid


def size_plan (column, command, by_range):
  """The size of the draw: what the results range gives, or the two fields
  that give it where the range names one cell."""
  rows, cols = (octave_stats.option_named (command, name)
                for name in octave_stats.ANALYSES[command]['sized'])
  if (by_range):
    column.block ('size_text', LEFT, COLUMN, LINE)
  else:
    column.put ('rows_label', LEFT, 26, LINE, label = rows['label'])
    column.put ('rows_draw', LEFT + 28, 40, BOX,
                help = rows.get ('help', rows['hint']))
    column.put ('cols_label', LEFT + 78, 40, LINE, label = cols['label'])
    column.block ('cols_draw', LEFT + 120, 40, BOX,
                  help = cols.get ('help', cols['hint']))
  column.hint ('size_hint', rows['hint'], rows.get ('help'))
  column.gap ()


def seed_plan (column, command):
  """The seed, under the size, in a field of its own."""
  seed = octave_stats.option_named (
    command, octave_stats.ANALYSES[command]['seeded'])
  column.put ('seed_label', LEFT, 26, LINE, label = seed['label'])
  column.block ('seed', LEFT + 28, 60, BOX,
                help = seed.get ('help', seed['hint']))
  column.hint ('seed_hint', seed['hint'], seed.get ('help'))
  column.gap ()


def options_plan (column, command):
  """The option rows, each as tall as what it draws and what it says."""
  options = octave_stats.slotted (command)
  if (not options):
    return
  column.block ('options_label', LEFT, COLUMN, LINE,
                label = octave_stats.heading (command))
  column.gap ()
  for slot, option in enumerate (options):
    option_plan (column, slot, option)
    column.gap ()


def option_plan (column, slot, option):
  """One option row, in the slot the dialog holds ready for it."""
  def named (kind):
    return 'option%d_%s' % (slot, kind)

  help_text = option.get ('help', option['hint'])
  if ('note' in option):
    column.put (named ('name'), LEFT, NAME_WIDTH, LINE,
                label = option['label'])
    column.put (named ('note'), NOTE_LEFT, NOTE_WIDTH, LINE,
                label = '(%s)' % option['note'])
    column.block (named ('value'), VALUE_LEFT, VALUE_WIDTH, BOX,
                  help = help_text)
    return
  kind = option['kind']
  if (kind in ('radios', 'checks')):
    column.block (named ('label'), LEFT, COLUMN, LINE + PAD,
                  label = option['label'])
    shown = 'radio%d' if kind == 'radios' else 'check%d'
    for place, (unused, label) in enumerate (option['choices']):
      column.block (named (shown % place), LEFT + CHOICE_INDENT,
                    COLUMN - CHOICE_INDENT, BOX, label = label,
                    help = help_text)
  elif (kind == 'choice'):
    wide = choice_width (option)
    column.put (named ('label'), LEFT, COLUMN - PAD - wide, LINE,
                label = option['label'])
    listed = option.get ('rows')
    column.block (named ('list' if listed else 'box'),
                  LEFT + COLUMN - wide, wide,
                  list_height (listed) if listed else BOX, help = help_text)
  else:
    column.put (named ('label'), LEFT, OPTION_LABEL_WIDTH, LINE,
                label = option['label'])
    column.block (named ('text'), LEFT + COLUMN - OPTION_WIDTH, OPTION_WIDTH,
                  BOX, help = help_text)
  column.hint (named ('hint'), option['hint'], option.get ('help'))


def custom_plan (column, command):
  """The Custom analysis draws its own side: what a slot may hold, the input
  slots and the pairs, then the output slots, each slot with a button that
  picks a range with the mouse."""
  column.block ('custom_intro', LEFT, COLUMN, words_height (CUSTOM_INTRO),
                label = CUSTOM_INTRO)
  column.gap ()
  column.block ('in_head', LEFT, COLUMN, LINE, label = INPUT_HEAD)
  column.gap ()
  for place in range (octave_stats.CUSTOM_SLOTS):
    slot_plan (column, 'in%d' % place,
               octave_stats.option_named (command, 'input%d' % (place + 1)),
               'Pick the range for input %d with the mouse.' % (place + 1))
  pairs = octave_stats.option_named (command, 'pairs')
  column.put ('pairs_label', LEFT, SLOT_LABEL, LINE, label = pairs['label'])
  column.block ('pairs_text', SLOT_LEFT, PAIRS_WIDTH, BOX,
                help = pairs.get ('help', pairs['hint']))
  column.hint ('pairs_hint', pairs['hint'])
  column.gap ()
  column.block ('out_head', LEFT, COLUMN, LINE, label = OUTPUT_HEAD)
  column.gap ()
  for place in range (octave_stats.CUSTOM_OUTPUTS):
    slot_plan (column, 'out%d' % place,
               octave_stats.option_named (command, 'output%d' % (place + 1)),
               'Pick the range for output %d with the mouse.' % (place + 1))
  column.hint ('out_hint', OUTPUT_HINT)
  return column.laid


def slot_plan (column, name, option, picking):
  """One Custom slot: its name, the field, and the button beside it."""
  column.put ('%s_label' % name, LEFT, SLOT_LABEL, LINE,
              label = option['label'])
  column.put ('%s_text' % name, SLOT_LEFT, SLOT_WIDTH, BOX,
              help = option.get ('help', option['hint']))
  column.block ('%s_pick' % name, PICK_LEFT, PICK_WIDTH, BUTTON,
                label = PICK, help = picking)
  column.gap ()


def bottom (laid):
  """Where the laid out column ends."""
  return max ((place['y'] + place['height'] for place in laid.values ()),
              default = TOP)
