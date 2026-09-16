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


def number (value):
  return {'kind': 'number', 'value': value}


def text (value):
  return {'kind': 'text', 'value': value}


EMPTY = {'kind': 'empty'}


class GroupArgs (unittest.TestCase):

  def test_numbers_and_empty_cells (self):
    args = octave_stats.group_args (((1.0, ''), (2.0, 3.0)), 'columns', 0, 0)
    self.assertEqual ((args[0]['rows'], args[0]['cols'], args[0]['cells']),
                      (2, 2, [number (1.0), EMPTY, number (2.0), number (3.0)]))

  def test_no_header_gives_empty_names (self):
    args = octave_stats.group_args (((1.0, 2.0),), 'columns', 0, 0)
    self.assertEqual ((len (args), args[2]), (3, octave_stats.NO_NAMES))

  def test_number_texts_read (self):
    args = octave_stats.group_args ((('Inf', '-inf'), ('NaN', 1.0)),
                                    'columns', 0, 0)
    self.assertEqual (str (args[0]['cells']),
                      str ([number (float ('inf')), number (float ('-inf')),
                            number (float ('nan')), number (1.0)]))

  def test_header_row_names (self):
    args = octave_stats.group_args ((('A', '', 2020.0), (1.0, 2.0, 3.0)),
                                    'columns', 0, 0)
    self.assertEqual ((args[0]['rows'], args[2]['cells']),
                      (1, [text ('A'), EMPTY, number (2020.0)]))

  def test_header_column_names (self):
    args = octave_stats.group_args ((('A', 1.0, 2.0), ('B', 3.0, 4.0)),
                                    'rows', 0, 0)
    self.assertEqual ((args[0]['cols'], args[2]['cells']),
                      (2, [text ('A'), text ('B')]))

  def test_text_refused_by_cell (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.group_args ((('A', 'B'), (1.0, 2.0), ('x', 3.0)),
                               'columns', 2, 4)
    self.assertEqual (str (raised.exception),
                      'C7 holds the text "x"; the input range may hold group '
                      'names in its first row, then numbers and empty cells '
                      'only.')

  def test_text_refused_by_cell_beside_header (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.group_args ((('A', 1.0), ('B', 'x')), 'rows', 2, 4)
    self.assertEqual (str (raised.exception),
                      'D6 holds the text "x"; the input range may hold group '
                      'names in its first column, then numbers and empty cells '
                      'only.')

  def test_header_only_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.group_args ((('A', 'B'),), 'columns', 0, 0)
    self.assertEqual (str (raised.exception),
                      'the input range holds only its header.')


class LabelsArgs (unittest.TestCase):

  def test_data_then_labels (self):
    args = octave_stats.labels_args (((1.0, 'a'), ('', 'b'), (2.0, 3.0)),
                                     'data-labels', 0, 0)
    self.assertEqual ((args[0]['rows'], args[0]['cols'], args[0]['cells']),
                      (3, 2, [number (1.0), text ('a'), EMPTY, text ('b'),
                              number (2.0), number (3.0)]))

  def test_labels_then_data (self):
    args = octave_stats.labels_args ((('a', 1.0), (2.0, 3.0)), 'labels-data',
                                     0, 0)
    self.assertEqual (args[0]['cells'], [number (1.0), text ('a'),
                                         number (3.0), number (2.0)])

  def test_labels_passed (self):
    args = octave_stats.labels_args (((1.0, 'a'),), 'data-labels', 0, 0)
    self.assertEqual (args[1:], [{'type': 'string', 'value': 'labels'},
                                 octave_stats.NO_NAMES])

  def test_number_texts_read (self):
    args = octave_stats.labels_args ((('-Inf', 'a'),), 'data-labels', 0, 0)
    self.assertEqual (args[0]['cells'][0], number (float ('-inf')))

  def test_header_ignored (self):
    args = octave_stats.labels_args ((('Group', 'Value'), ('a', 1.0)),
                                     'labels-data', 0, 0)
    self.assertEqual (args[0]['cells'], [number (1.0), text ('a')])

  def test_header_only_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.labels_args ((('Value', 'Group'),), 'data-labels', 0, 0)
    self.assertEqual (str (raised.exception),
                      'the input range holds only its header.')

  def test_width_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.labels_args (((1.0, 'a', 2.0),), 'data-labels', 0, 0)
    self.assertEqual (str (raised.exception),
                      'grouped by labels, the input range must be two columns '
                      'wide: the values and their group labels.')

  def test_text_value_refused_by_cell (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.labels_args (((1.0, 'a'), ('x', 'b')), 'data-labels', 2, 4)
    self.assertEqual (str (raised.exception),
                      'C6 holds the text "x"; the values may be numbers or '
                      'empty cells, and the group labels text or numbers.')

  def test_value_without_label_refused_by_cell (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.labels_args ((('a', 1.0), ('', 2.0)), 'labels-data', 2, 4)
    self.assertEqual (str (raised.exception),
                      'D6 holds a value with no group label in C6.')


class Registry (unittest.TestCase):

  def test_every_analysis_is_complete (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      self.assertEqual (sorted (analysis),
                        ['category', 'detail', 'function', 'layouts',
                         'options', 'title'], command)
      self.assertIn (analysis['category'], octave_stats.CATEGORIES, command)
      self.assertTrue (set (analysis['layouts']) <= set (octave_stats.BY),
                       command)

  def test_every_category_is_described (self):
    for category, description in octave_stats.CATEGORIES.items ():
      self.assertTrue (description.endswith ('.'), category)

  def test_category_names_in_order (self):
    self.assertEqual (octave_stats.category_names ()[0], 'Group comparisons')

  def test_analyses_of_category (self):
    self.assertEqual (octave_stats.analyses_of ('Group comparisons'),
                      ('KruskalWallis', 'Anova1'))

  def test_options_fit_the_dialog (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      self.assertLessEqual (len (analysis['options']), 3, command)

  def test_analyses_of_empty_category (self):
    self.assertEqual (octave_stats.analyses_of ('Distributions'), ())

  def test_first_analysis (self):
    self.assertEqual (octave_stats.first_analysis (), 'KruskalWallis')

  def test_every_option_is_complete (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      for option in analysis['options']:
        self.assertTrue ({'name', 'kind', 'label', 'hint', 'default'}
                         <= set (option), option)
        self.assertIn (option['kind'], ('choice', 'number'), option['name'])

  def test_option_defaults (self):
    self.assertEqual (octave_stats.option_defaults ('KruskalWallis'),
                      {'ctype': 'holm', 'alpha': '0.05'})

  def test_option_args_of_kruskalwallis (self):
    self.assertEqual (octave_stats.option_args ('KruskalWallis', {}),
                      [{'type': 'string', 'value': 'holm'},
                       {'type': 'number', 'value': 0.05}])


class DeclaredOptions (unittest.TestCase):
  """The option mechanism, against a declaration of its own, since no
  analysis declares options yet."""

  DECLARED = {'category': 'Group comparisons', 'title': 'Test', 'function': 'f',
              'detail': 'What it does.', 'layouts': ('columns',),
              'options': ({'name': 'ctype', 'kind': 'choice',
                           'label': 'Adjustment:', 'hint': 'How adjusted.',
                           'choices': (('holm', 'Holm'),
                                       ('bonferroni', 'Bonferroni')),
                           'default': 'holm'},)}

  def setUp (self):
    octave_stats.ANALYSES['Declared'] = self.DECLARED

  def tearDown (self):
    del octave_stats.ANALYSES['Declared']

  def test_defaults (self):
    self.assertEqual (octave_stats.option_defaults ('Declared'),
                      {'ctype': 'holm'})

  def test_chosen_value_passed (self):
    self.assertEqual (octave_stats.option_args ('Declared',
                                                {'ctype': 'bonferroni'}),
                      [{'type': 'string', 'value': 'bonferroni'}])

  def test_default_passed_when_unset (self):
    self.assertEqual (octave_stats.option_args ('Declared', {}),
                      [{'type': 'string', 'value': 'holm'}])

  def test_value_not_offered_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.option_args ('Declared', {'ctype': 'tukey'})
    self.assertEqual (str (raised.exception),
                      'tukey is not a value of "ctype".')


class NumberOption (unittest.TestCase):

  OPTION = {'name': 'alpha', 'kind': 'number', 'label': 'Significance level:',
            'hint': 'Sets the intervals.',
            'accepts': 'a number greater than 0 and less than 1',
            'minimum': 0.0, 'maximum': 1.0, 'default': '0.05'}

  def test_typed_number (self):
    self.assertEqual (octave_stats.option_number (self.OPTION, '0.01'), 0.01)

  def test_comma_for_decimal_point (self):
    self.assertEqual (octave_stats.option_number (self.OPTION, '0,01'), 0.01)

  def test_out_of_range_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.option_number (self.OPTION, '1')
    self.assertEqual (str (raised.exception),
                      'the significance level must be a number greater than 0 '
                      'and less than 1.')

  def test_not_a_number_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.option_number (self.OPTION, 'small')
    self.assertEqual (str (raised.exception),
                      'the significance level must be a number greater than 0 '
                      'and less than 1.')


class AnalysisArgs (unittest.TestCase):

  def test_grouping_passed (self):
    args = octave_stats.analysis_args (((1.0, 2.0),), 'rows', 0, 0)
    self.assertEqual (args[1], {'type': 'string', 'value': 'rows'})

  def test_grouping_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.analysis_args (((1.0, 2.0),), 'diagonal', 0, 0)
    self.assertEqual (str (raised.exception),
                      'grouped by must be "columns", "rows", "labels-data" or '
                      '"data-labels".')


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
class AnalysesInOctave (unittest.TestCase):

  @classmethod
  def setUpClass (cls):
    cls.runner = octave_core.Server (
      {'folders': [os.path.join (ROOT, 'octave')],
       'packages': [octave_stats.PACKAGE], 'memory': 2, 'tmp': 2,
       'seconds': 60})

  @classmethod
  def tearDownClass (cls):
    cls.runner.stop ()

  def run_analysis (self, rows, by, command = 'KruskalWallis'):
    args = (octave_stats.analysis_args (rows, by, 0, 0)
            + octave_stats.option_args (command, {}))
    return octave_stats.results (
      self.runner.call (octave_stats.ANALYSES[command]['function'], args))

  def test_anova_reaches_cells (self):
    table = self.run_analysis (((1.0, 4.0, 7.0), (2.0, 5.0, 9.0),
                                (3.0, 6.0, 8.0)), 'columns', 'Anova1')
    self.assertEqual ((table[0][0], table[3][:3]),
                      ('One-way ANOVA', ('Column 1', 3.0, 2.0)))

  def test_results_reach_cells (self):
    table = self.run_analysis (((1.0, 4.0, 7.0), (2.0, 5.0, 8.0),
                                (3.0, '', 9.0)), 'columns')
    self.assertEqual (table[0][0], 'Kruskal-Wallis Test')
    self.assertEqual (table[3][:4], ('Column 1', 3.0, 2.0, 2.0))
    self.assertEqual (table[4][:4], ('Column 2', 2.0, 4.5, 4.5))

  def test_names_reach_cells (self):
    table = self.run_analysis ((('A', '', 2020.0), (1.0, 4.0, 7.0),
                                (2.0, 5.0, 8.0)), 'columns')
    self.assertEqual ([line[0] for line in table[3:6]],
                      ['A', 'Column 2', '2020'])

  def test_labels_reach_cells (self):
    table = self.run_analysis ((('Value', 'Group'), (7.0, 'b'), (1.0, 2.0),
                                ('', ''), (8.0, 'b'), (2.0, 2.0)),
                               'data-labels')
    self.assertEqual ((table[3][:3], table[4][:3]),
                      (('b', 2.0, 7.5), ('2', 2.0, 1.5)))

  def test_refusal_names_no_function (self):
    with self.assertRaises (RuntimeError) as raised:
      self.run_analysis (((1.0,), (2.0,)), 'columns')
    self.assertEqual (
      octave_stats.reason (str (raised.exception),
                           'octave_calc_kruskalwallis'),
      'the input range holds fewer than two groups.')


if (__name__ == '__main__'):
  unittest.main ()
