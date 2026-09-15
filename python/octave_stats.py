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

# Each menu command, against its title and the Octave function that runs it.
ANALYSES = {'KruskalWallis': ('Kruskal-Wallis Test',
                              'octave_calc_kruskalwallis')}


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
  args = [octave_core.range_arg (
            [[number_cell (value, left + c, top + r, ALLOWED[by])
              for c, value in enumerate (values)]
             for r, values in enumerate (body)]),
          {'type': 'string', 'value': by}]
  if (named):
    args.append (octave_core.range_arg (
      [[octave_core.plain_cell (value) for value in header]]))
  return args


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
  return [octave_core.range_arg (cells), {'type': 'string', 'value': 'labels'}]


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
