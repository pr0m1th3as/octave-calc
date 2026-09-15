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
refusal names the cell, and turned into that function's arguments.
"""

import octave_core

# The Octave package every analysis loads in its sandbox.
PACKAGE = 'statistics'

# How the input range is split into samples, as Calc's own dialogs offer.
BY = ('columns', 'rows')

# Each menu command, against its title and the Octave function that runs it.
ANALYSES = {'KruskalWallis': ('Kruskal-Wallis Test',
                              'octave_calc_kruskalwallis')}


def data_arg (rows, column, row):
  """The range argument for an input range holding ROWS of values, as
  getDataArray gives them, where an empty cell is empty text.  COLUMN and ROW
  place the range's top-left cell on its sheet.  Raises ValueError on a cell
  holding text."""
  cells = []
  for r, values in enumerate (rows):
    line = []
    for c, value in enumerate (values):
      if (isinstance (value, str)):
        if (value != ''):
          raise ValueError ('%s holds the text "%s"; the input range may hold '
                            'numbers and empty cells only.'
                            % (octave_core.cell_name (column + c, row + r),
                               value))
        line.append ({'kind': 'empty'})
      else:
        line.append ({'kind': 'number', 'value': float (value)})
    cells.append (line)
  return octave_core.range_arg (cells)


def analysis_args (rows, by, column, row):
  """The octave_call arguments of an analysis function: the input range ROWS,
  whose top-left cell is at COLUMN and ROW, and how BY splits it into
  samples.  Raises ValueError."""
  if (by not in BY):
    raise ValueError ('grouped by must be "columns" or "rows".')
  return [data_arg (rows, column, row), {'type': 'string', 'value': by}]


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
