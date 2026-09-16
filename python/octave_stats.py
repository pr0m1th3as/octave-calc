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

"""The analyses under Data > Statistics with GNU Octave, and nothing about
LibreOffice.

Each analysis is an Octave function in the extension's octave folder, which
runs the statistics package and returns its results laid out as the cells a
Calc user sees.  Here the input range is checked cell by cell, so that a
refusal names the cell, and turned into that function's arguments.  The
analysis itself, grouping included, is the Octave function's.
"""

import octave_core

# The Octave package every analysis loads in its sandbox.
PACKAGE = 'statistics'

# How the input range holds the groups: one per column or one per row, each
# may be headed by its name, or two columns, each value beside the label of
# its group, in either order.
BY = ('columns', 'rows', 'labels-data', 'data-labels')

# What each way of grouping allows in the input range, ending a refusal.
ALLOWED = {'columns': 'the input range may hold group names in its first row, '
                      'then numbers and empty cells only.',
           'rows': 'the input range may hold group names in its first column, '
                   'then numbers and empty cells only.',
           'labels-data': 'the values may be numbers or empty cells, and the '
                          'group labels text or numbers.',
           'data-labels': 'the values may be numbers or empty cells, and the '
                          'group labels text or numbers.'}

# The categories, in the order the dialog lists them, each with the sentence
# shown under the category.
CATEGORIES = {
  'Group comparisons':
    'Tests whether two or more groups differ, and which of them do.',
  'Association tests':
    'Measures whether two variables move together, and tests independence.',
  'Regression models':
    'Fits a model that predicts one variable from others.',
  'Multivariate analyses':
    'Finds the structure in many variables at once.',
  'Distributions':
    'Fits a distribution to a sample, and tests whether it fits.',
  'Experimental design':
    'Plans a study before the data exist: how many observations are needed, '
    'and which combinations to run.'}


def category_names ():
  """The categories in the order the dialog lists them."""
  return tuple (CATEGORIES)

# Every analysis, by the command that runs it, in the order its category lists
# them.  Adding one is this entry plus its Octave function, and nothing else:
#
#   category  which list it appears under
#   title     the dialog's title and the first cell of the results
#   function  the Octave function in the octave folder
#   detail    what it does and when to use it, shown under the list
#   input     'range', the analysis reads the cells of an input range, or
#             'none', it takes its options alone and reads no cells
#   layouts   the ways it takes its input range, from BY, or () when it reads
#             no cells
#   options   what the user chooses besides the ranges, passed to the function
#             after the range, the layout and the names, in declared order.
#             Each carries 'name', 'label', 'hint', 'default' and a 'kind':
#             'choice' holds 'choices', ((value, label), ...), and reaches the
#             function as text; 'number' holds 'minimum', 'maximum' and
#             'accepts', the refusal's words, and reaches it as a number,
#             whole when it holds 'whole'; 'numbers' holds the same and
#             reaches the function as a range of one row
ANALYSES = {
  'KruskalWallis': {
    'category': 'Group comparisons',
    'input': 'range',
    'title': 'Kruskal-Wallis Test',
    'function': 'octave_calc_kruskalwallis',
    'detail': 'Compares three or more independent groups by rank, without '
              'assuming the values are normally distributed.\n\n'
              'Use it when the groups are independent, the values are at '
              'least ordinal, and the data are skewed, heavy tailed, or too '
              'few to judge. It answers whether any group differs; the '
              'pairwise comparisons say which.\n\n'
              'For two groups use the Mann-Whitney U test. For normally '
              'distributed values, one-way ANOVA is more powerful.',
    'layouts': BY,
    'options': (
      {'name': 'ctype', 'kind': 'choice', 'label': 'Comparisons:',
       'hint': 'How the p-values of the pairwise comparisons are adjusted.',
       'choices': (('holm', 'Holm'), ('bonferroni', 'Bonferroni'),
                   ('scheffe', 'Scheffe'), ('mvt', 'Multivariate t'),
                   ('hochberg', 'Hochberg'), ('fdr', 'False discovery rate'),
                   ('lsd', 'None')),
       'default': 'holm'},
      {'name': 'alpha', 'kind': 'number', 'label': 'Significance level:',
       'hint': 'Sets the confidence intervals. 0.05 by default.',
       'accepts': 'a number greater than 0 and less than 1',
       'minimum': 0.0, 'maximum': 1.0, 'default': '0.05'})},
  'Anova1': {
    'category': 'Group comparisons',
    'input': 'range',
    'title': 'One-way ANOVA',
    'function': 'octave_calc_anova1',
    'detail': 'Compares the means of two or more independent groups, by '
              'weighing the spread between the groups against the spread '
              'within them.\n\n'
              'Use it when the groups are independent, the values are '
              'measured on a scale, and each group is roughly normal. It '
              'answers whether any mean differs; the pairwise comparisons '
              'say which.\n\n'
              'When the groups have unequal variances, choose Welch. When '
              'the data are skewed or few, the Kruskal-Wallis Test is '
              'safer.',
    'layouts': BY,
    'options': (
      {'name': 'ctype', 'kind': 'choice', 'label': 'Comparisons:',
       'hint': 'How the p-values of the pairwise comparisons are adjusted.',
       'choices': (('holm', 'Holm'), ('bonferroni', 'Bonferroni'),
                   ('scheffe', 'Scheffe'), ('mvt', 'Multivariate t'),
                   ('hochberg', 'Hochberg'), ('fdr', 'False discovery rate'),
                   ('lsd', 'None')),
       'default': 'holm'},
      {'name': 'alpha', 'kind': 'number', 'label': 'Significance level:',
       'hint': 'Sets the confidence intervals. 0.05 by default.',
       'accepts': 'a number greater than 0 and less than 1',
       'minimum': 0.0, 'maximum': 1.0, 'default': '0.05'},
      {'name': 'vartype', 'kind': 'choice', 'label': 'Variances:',
       'hint': 'Welch does not assume the groups share a variance.',
       'choices': (('equal', 'equal (assumed)'),
                   ('unequal', 'non-equal (Welch)')),
       'default': 'equal'})},
  'FullFactorial': {
    'category': 'Experimental design',
    'title': 'Full factorial design',
    'function': 'octave_calc_fullfact',
    'input': 'none',
    'detail': 'Writes every combination of the levels of each factor, one '
              'run per row.\n\n'
              'Use it to lay out a study before running it, when every '
              'factor is to be crossed with every other. Three factors of 2, '
              '3 and 3 levels give 18 runs.\n\n'
              'For factors of two levels each, the two-level design is '
              'shorter to ask for.',
    'layouts': (),
    'options': (
      {'name': 'levels', 'kind': 'numbers', 'label': 'Levels per factor:',
       'hint': 'One number per factor, such as 2 3 3.',
       'accepts': 'one whole number per factor, each 2 or more',
       'minimum': 1.0, 'maximum': 1000.0, 'whole': True, 'default': '2 3 3'},)},
  'TwoLevelFactorial': {
    'category': 'Experimental design',
    'title': 'Two-level factorial design',
    'function': 'octave_calc_ff2n',
    'input': 'none',
    'detail': 'Writes every combination of two levels, 0 and 1, of the given '
              'number of factors, one run per row.\n\n'
              'Use it for a screening study where each factor is set low or '
              'high. Five factors give 32 runs, and the count doubles with '
              'each factor added.',
    'layouts': (),
    'options': (
      {'name': 'factors', 'kind': 'number', 'label': 'Factors:',
       'hint': 'Each factor doubles the number of runs.',
       'accepts': 'a whole number from 1 to 15',
       'minimum': 0.0, 'maximum': 16.0, 'whole': True, 'default': '3'},)}}


def first_analysis ():
  """The command the dialog opens on: the first analysis of the first
  category that has one."""
  for category in CATEGORIES:
    commands = analyses_of (category)
    if (commands):
      return commands[0]
  return None


def analyses_of (category):
  """The commands of CATEGORY, in order."""
  return tuple (command for command, analysis in ANALYSES.items ()
                if analysis['category'] == category)


def option_defaults (command):
  """What the options of COMMAND hold before the user touches them."""
  return dict ((option['name'], option['default'])
               for option in ANALYSES[command]['options'])


def option_number (option, value):
  """VALUE as the number OPTION takes, from the dialog's text or a number.
  Raises ValueError saying what the option accepts."""
  return option_numbers (option, value)[0]


def option_numbers (option, value):
  """VALUE as the list of numbers OPTION takes, from the dialog's text, where
  they are written one after another, or from numbers already.  Raises
  ValueError saying what the option accepts."""
  what = option['label'].rstrip (':').lower ()
  refusal = ValueError ('the %s must be %s.' % (what, option['accepts']))
  if (option['kind'] == 'number'):
    # One number, where a comma is the decimal point a Greek locale types
    words = [str (value).strip ().replace (',', '.')]
  else:
    words = str (value).replace (',', ' ').replace (';', ' ').split ()
  if (not words or not words[0]):
    raise refusal
  numbers = []
  for word in words:
    try:
      number = float (word)
    except ValueError:
      raise refusal
    if (not (option['minimum'] < number < option['maximum'])):
      raise refusal
    if (option.get ('whole') and number != int (number)):
      raise refusal
    numbers.append (number)
  if (option['kind'] == 'number' and len (numbers) != 1):
    raise refusal
  return numbers


def option_args (command, values):
  """The octave_call arguments for the options of COMMAND, in declared order,
  from VALUES as the dialog holds them.  An option the user has not set takes
  its default.  Raises ValueError on a value the option does not take."""
  args = []
  for option in ANALYSES[command]['options']:
    value = values.get (option['name'], option['default'])
    if (option['kind'] == 'number'):
      args.append ({'type': 'number', 'value': option_number (option, value)})
      continue
    if (option['kind'] == 'numbers'):
      args.append (octave_core.range_arg (
        [[{'kind': 'number', 'value': number}
          for number in option_numbers (option, value)]]))
      continue
    if (value not in [choice for choice, unused in option['choices']]):
      raise ValueError ('%s is not a value of "%s".' % (value, option['name']))
    args.append ({'type': 'string', 'value': value})
  return args


# An analysis function always takes the range, the layout and the group names,
# so that the options an analysis declares follow at fixed positions.  This
# stands for no names at all: empty text, since a range must hold a cell.
NO_NAMES = {'type': 'string', 'value': ''}


def is_name (value):
  """True when VALUE, as getDataArray gives it, is text that cannot be read
  as a number, and so a name."""
  return (isinstance (value, str) and value != ''
          and value.lower () not in octave_core.NUMBER_TEXTS)


def number_cell (value, column, row, allowed):
  """The range cell for VALUE, as getDataArray gives it, at COLUMN and ROW on
  its sheet: a number, Inf, -Inf or NaN written as text, or empty.  Raises
  ValueError, ending with ALLOWED, on any other text."""
  if (isinstance (value, str)):
    if (value == ''):
      return {'kind': 'empty'}
    if (not is_name (value)):
      return {'kind': 'number',
              'value': octave_core.NUMBER_TEXTS[value.lower ()]}
    raise ValueError ('%s holds the text "%s"; %s'
                      % (octave_core.cell_name (column, row), value, allowed))
  return {'kind': 'number', 'value': float (value)}


def header_only ():
  return ValueError ('the input range holds only its header.')


def group_args (rows, by, column, row):
  """The arguments for one group per column or, when BY is 'rows', per row,
  from ROWS whose top-left cell is at COLUMN and ROW.  A first row, or first
  column, holding a name is the header, passed as the groups' names."""
  if (by == 'rows'):
    header = [values[0] for values in rows]
    body = [values[1:] for values in rows]
    left, top = column + 1, row
  else:
    header = list (rows[0])
    body = rows[1:]
    left, top = column, row + 1
  named = any (is_name (value) for value in header)
  if (not named):
    body, left, top = rows, column, row
  if (not body or not body[0]):
    raise header_only ()
  names = NO_NAMES
  if (named):
    names = octave_core.range_arg (
      [[octave_core.plain_cell (value) for value in header]])
  return [octave_core.range_arg (
            [[number_cell (value, left + c, top + r, ALLOWED[by])
              for c, value in enumerate (values)]
             for r, values in enumerate (body)]),
          {'type': 'string', 'value': by}, names]


def labels_args (rows, by, column, row):
  """The arguments for two columns, each value beside the label of its
  group, from ROWS whose top-left cell is at COLUMN and ROW; BY says which
  column holds the labels.  The values go first.  A first row whose value is
  a name is a header, and ignored."""
  if (len (rows[0]) != 2):
    raise ValueError ('grouped by labels, the input range must be two columns '
                      'wide: the values and their group labels.')
  at = 0 if by == 'labels-data' else 1
  start = 1 if is_name (rows[0][1 - at]) else 0
  if (start == len (rows)):
    raise header_only ()
  cells = []
  for r in range (start, len (rows)):
    label = rows[r][at]
    number = number_cell (rows[r][1 - at], column + 1 - at, row + r,
                          ALLOWED[by])
    if (number['kind'] == 'number' and label == ''):
      raise ValueError ('%s holds a value with no group label in %s.'
                        % (octave_core.cell_name (column + 1 - at, row + r),
                           octave_core.cell_name (column + at, row + r)))
    cells.append ([number, octave_core.plain_cell (label)])
  return [octave_core.range_arg (cells), {'type': 'string', 'value': 'labels'},
          NO_NAMES]


def analysis_args (rows, by, column, row):
  """The octave_call arguments of an analysis function: the input range ROWS,
  whose top-left cell is at COLUMN and ROW, and how BY says it holds the
  groups.  Raises ValueError."""
  if (by not in BY):
    raise ValueError ('grouped by must be "columns", "rows", "labels-data" or '
                      '"data-labels".')
  if (by in ('columns', 'rows')):
    return group_args (rows, by, column, row)
  return labels_args (rows, by, column, row)


def results (outputs):
  """The rows of cells an analysis function returned as its only output."""
  return octave_core.output_rows (outputs[0])


def reason (message, function):
  """MESSAGE from Octave without the name of FUNCTION in front of it, which
  names nothing a Calc user has seen."""
  prefix = function + ': '
  return message[len (prefix):] if message.startswith (prefix) else message


def overlaps (first, second):
  """True when two ranges share a cell, each given as its sheet, first column,
  first row, last column and last row."""
  return (first[0] == second[0]
          and first[1] <= second[3] and second[1] <= first[3]
          and first[2] <= second[4] and second[2] <= first[4])
