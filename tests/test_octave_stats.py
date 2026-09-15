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

"""Tests for octave_stats.  From the repository root:

  python3 -m unittest discover tests

The tests that run Octave do so in the real sandboxed devtools server with the
statistics package and the extension's octave folder, and are skipped where no
sandbox can run.  The analysis functions carry their own BISTs.
"""

import os
import sys
import unittest

ROOT = os.path.dirname (os.path.dirname (os.path.abspath (__file__)))
sys.path.insert (0, os.path.join (ROOT, 'python'))

import octave_core
import octave_stats


class DataArg (unittest.TestCase):

  def test_numbers_and_empty_cells (self):
    arg = octave_stats.data_arg (((1.0, ''), (2.0, 3.0)), 0, 0)
    self.assertEqual ((arg['rows'], arg['cols']), (2, 2))
    self.assertEqual (arg['cells'], [{'kind': 'number', 'value': 1.0},
                                     {'kind': 'empty'},
                                     {'kind': 'number', 'value': 2.0},
                                     {'kind': 'number', 'value': 3.0}])

  def test_text_refused_by_cell (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.data_arg (((1.0, 2.0), ('x', 3.0)), 2, 4)
    self.assertEqual (str (raised.exception),
                      'C6 holds the text "x"; the input range may hold numbers '
                      'and empty cells only.')


class AnalysisArgs (unittest.TestCase):

  def test_grouping_passed (self):
    args = octave_stats.analysis_args (((1.0, 2.0),), 'rows', 0, 0)
    self.assertEqual (args[1], {'type': 'string', 'value': 'rows'})

  def test_grouping_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.analysis_args (((1.0, 2.0),), 'diagonal', 0, 0)
    self.assertEqual (str (raised.exception),
                      'grouped by must be "columns" or "rows".')


class Reason (unittest.TestCase):

  def test_function_name_removed (self):
    self.assertEqual (octave_stats.reason ('f: the range is empty.', 'f'),
                      'the range is empty.')

  def test_other_message_kept (self):
    self.assertEqual (octave_stats.reason ('out of memory.', 'f'),
                      'out of memory.')


class Overlaps (unittest.TestCase):

  def test_shared_cell (self):
    self.assertTrue (octave_stats.overlaps ((0, 0, 0, 2, 9), (0, 2, 9, 7, 20)))

  def test_beside (self):
    self.assertFalse (octave_stats.overlaps ((0, 0, 0, 2, 9), (0, 3, 0, 8, 10)))

  def test_other_sheet (self):
    self.assertFalse (octave_stats.overlaps ((0, 0, 0, 2, 9), (1, 0, 0, 2, 9)))


@unittest.skipUnless (octave_core.sandbox_problem () is None,
                      'no sandbox on this machine')
class KruskalWallisInOctave (unittest.TestCase):

  @classmethod
  def setUpClass (cls):
    cls.runner = octave_core.Server (
      {'folders': [os.path.join (ROOT, 'octave')],
       'packages': [octave_stats.PACKAGE], 'memory': 2, 'tmp': 2,
       'seconds': 60})

  @classmethod
  def tearDownClass (cls):
    cls.runner.stop ()

  def run_analysis (self, rows, by):
    args = octave_stats.analysis_args (rows, by, 0, 0)
    return octave_stats.results (
      self.runner.call ('octave_calc_kruskalwallis', args))

  def test_results_reach_cells (self):
    table = self.run_analysis (((1.0, 4.0, 7.0), (2.0, 5.0, 8.0),
                                (3.0, '', 9.0)), 'columns')
    self.assertEqual (table[0][0], 'Kruskal-Wallis Test')
    self.assertEqual (table[3][:4], ('Column 1', 3.0, 2.0, 2.0))
    self.assertEqual (table[4][:4], ('Column 2', 2.0, 4.5, 4.5))

  def test_refusal_names_no_function (self):
    with self.assertRaises (RuntimeError) as raised:
      self.run_analysis (((1.0,), (2.0,)), 'columns')
    self.assertEqual (
      octave_stats.reason (str (raised.exception),
                           'octave_calc_kruskalwallis'),
      'the input range holds fewer than two groups.')


if (__name__ == '__main__'):
  unittest.main ()
