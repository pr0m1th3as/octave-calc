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

import importlib.util
import math
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


class FactorArgs (unittest.TestCase):
  """A value beside the two factors it was measured under, read from the
  cells and turned into the arguments of a two-factor analysis."""

  def args (self, rows, by = 'data-labels', column = 0, row = 0):
    return octave_stats.analysis_args (rows, by, column, row, 'factors')

  def test_values_first_whichever_way_round (self):
    given = self.args (((5.0, 'a', 'x'), (7.0, 'b', 'y')))
    after = self.args ((('a', 'x', 5.0), ('b', 'y', 7.0)), 'labels-data')
    self.assertEqual (given, after)

  def test_layout_reaches_octave_as_labels (self):
    self.assertEqual (self.args (((5.0, 'a', 'x'), (7.0, 'b', 'y')))[1],
                      {'type': 'string', 'value': 'labels'})

  def test_header_names_the_factors (self):
    args = self.args ((('Yield', 'Fert', 'Var'), (5.0, 'a', 'x'),
                       (7.0, 'b', 'y')))
    self.assertEqual (args[2]['cells'], [text ('Fert'), text ('Var')])

  def test_no_header_gives_no_names (self):
    self.assertEqual (self.args (((5.0, 'a', 'x'), (7.0, 'b', 'y')))[2],
                      octave_stats.NO_NAMES)

  def test_width_refused (self):
    with self.assertRaises (ValueError) as raised:
      self.args (((5.0, 'a'), (7.0, 'b')))
    self.assertEqual (str (raised.exception),
                      'with two factors the input range must be three '
                      'columns wide: the values and the two factors of each.')

  def test_value_without_a_factor_refused_by_cell (self):
    with self.assertRaises (ValueError) as raised:
      self.args (((5.0, 'a', 'x'), (7.0, 'b', '')), 'data-labels', 2, 4)
    self.assertEqual (str (raised.exception),
                      'C6 holds a value with no factor in E6.')

  def test_text_value_refused_by_cell (self):
    with self.assertRaises (ValueError) as raised:
      self.args (((5.0, 'a', 'x'), ('oops', 'b', 'y')))
    self.assertEqual (str (raised.exception),
                      'A2 holds the text "oops"; the values may be numbers '
                      'or empty cells, and the factor labels text or '
                      'numbers.')

  def test_header_only_refused (self):
    with self.assertRaises (ValueError) as raised:
      self.args ((('Yield', 'Fert', 'Var'),))
    self.assertEqual (str (raised.exception),
                      'the input range holds only its header.')


class Packaged (unittest.TestCase):
  """Every registered analysis reaches the .oxt.  A menu entry whose Octave
  function was left out of the package offers an analysis that cannot run,
  and nothing before this said so."""

  def setUp (self):
    spec = importlib.util.spec_from_file_location (
      'build_oxt', os.path.join (ROOT, 'tools', 'build_oxt.py'))
    self.build = importlib.util.module_from_spec (spec)
    spec.loader.exec_module (self.build)

  def test_every_analysis_function_is_packaged (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      self.assertIn ('octave/%s.m' % analysis['function'],
                     self.build.CONTENT, command)

  def test_every_octave_file_is_packaged (self):
    for folder, published in (('octave', 'octave/%s'),
                              (os.path.join ('octave', 'private'),
                               'octave/private/%s')):
      for name in os.listdir (os.path.join (ROOT, folder)):
        if (name.endswith ('.m')):
          self.assertIn (published % name, self.build.CONTENT, name)

  def test_every_packaged_source_exists (self):
    for published, source in self.build.CONTENT.items ():
      if ('build' not in source):
        self.assertTrue (os.path.exists (source), published)


class Registry (unittest.TestCase):

  def test_every_analysis_is_complete (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      self.assertEqual (sorted (set (analysis) - {'sized'}),
                        ['category', 'detail', 'function', 'input', 'layouts',
                         'options', 'title'], command)
      for name in analysis.get ('sized', ()):
        self.assertIn (name, [option['name']
                              for option in analysis['options']], command)
      self.assertIn (analysis['input'], octave_stats.INPUTS, command)
      self.assertEqual (analysis['input'] == 'none',
                        analysis['layouts'] == (), command)
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
                      ('KruskalWallis', 'Anova1', 'Ttest2', 'Ranksum',
                       'VarTestN', 'Anova2', 'TtestPaired', 'SignRank',
                       'SignTest', 'Friedman', 'Ttest1'))

  def test_analyses_of_distribution_fitting (self):
    self.assertEqual (octave_stats.analyses_of ('Distribution fitting'),
                      ('Normality', 'Chi2gof', 'Fitdist', 'Isoutlier'))

  def test_sample_analyses_take_no_label_layout (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      if (analysis['input'] == 'sample'):
        self.assertEqual (analysis['layouts'], ('columns', 'rows'), command)

  def test_option_args_of_ttest1 (self):
    self.assertEqual (octave_stats.option_args ('Ttest1', {}),
                      [{'type': 'number', 'value': 0.0},
                       {'type': 'string', 'value': 'both'},
                       {'type': 'number', 'value': 0.05}])

  def test_option_args_of_fitdist (self):
    self.assertEqual (octave_stats.option_args ('Fitdist', {}),
                      [{'type': 'string', 'value': 'Normal'},
                       {'type': 'string', 'value': 'none'},
                       {'type': 'number', 'value': 0.05}])

  def test_option_args_of_isoutlier (self):
    self.assertEqual (octave_stats.option_args ('Isoutlier', {}),
                      [{'type': 'string', 'value': 'median'},
                       {'type': 'number', 'value': 0.0}])

  def test_sample_refusal_names_the_sample (self):
    self.assertIn ('sample names', octave_stats.allowed ('columns', 'sample'))

  def test_options_fit_the_dialog (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      self.assertLessEqual (len (analysis['options']), 6, command)

  def test_analyses_of_experimental_design (self):
    self.assertEqual (octave_stats.analyses_of ('Experimental design'),
                      ('FullFactorial', 'TwoLevelFactorial', 'SampleSize',
                       'TestPower', 'Detectable'))

  def test_power_options_reach_octave_in_order (self):
    args = octave_stats.option_args ('SampleSize', {})
    self.assertEqual ([arg['value'] for arg in args],
                      ['t', 5.0, 2.0, 6.0, 0.9, 0.05])

  def test_analyses_of_random_numbers (self):
    self.assertEqual (octave_stats.analyses_of ('Random numbers'),
                      ('RandomNumbers',))

  def test_analyses_of_empty_category (self):
    self.assertEqual (octave_stats.analyses_of ('Association tests'), ())

  def test_first_analysis (self):
    self.assertEqual (octave_stats.first_analysis (), 'KruskalWallis')

  def test_every_option_is_complete (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      for option in analysis['options']:
        self.assertTrue ({'name', 'kind', 'label', 'hint', 'default'}
                         <= set (option), option)
        self.assertIn (option['kind'], ('choice', 'number', 'numbers'),
                     option['name'])

  def test_option_defaults (self):
    self.assertEqual (octave_stats.option_defaults ('KruskalWallis'),
                      {'ctype': 'holm', 'alpha': '0.05'})

  def test_option_args_of_kruskalwallis (self):
    self.assertEqual (octave_stats.option_args ('KruskalWallis', {}),
                      [{'type': 'string', 'value': 'holm'},
                       {'type': 'number', 'value': 0.05}])

  def test_option_args_of_ttest2 (self):
    self.assertEqual (octave_stats.option_args ('Ttest2', {}),
                      [{'type': 'string', 'value': 'equal'},
                       {'type': 'string', 'value': 'both'},
                       {'type': 'number', 'value': 0.05}])

  def test_option_args_of_ranksum (self):
    self.assertEqual (octave_stats.option_args ('Ranksum', {}),
                      [{'type': 'string', 'value': 'auto'},
                       {'type': 'string', 'value': 'both'},
                       {'type': 'number', 'value': 0.05}])

  def test_option_args_of_vartestn (self):
    self.assertEqual (octave_stats.option_args ('VarTestN', {}),
                      [{'type': 'string', 'value': 'Bartlett'},
                       {'type': 'number', 'value': 0.05}])

  def test_two_factor_analyses_take_the_label_layouts (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      if (analysis['input'] == 'factors'):
        self.assertEqual (analysis['layouts'],
                          ('labels-data', 'data-labels'), command)

  def test_option_args_of_anova2 (self):
    self.assertEqual (octave_stats.option_args ('Anova2', {}),
                      [{'type': 'string', 'value': 'interaction'},
                       {'type': 'string', 'value': 'holm'},
                       {'type': 'number', 'value': 0.05}])

  def test_factor_refusal_names_factors (self):
    self.assertIn ('factor labels',
                   octave_stats.allowed ('labels-data', 'factors'))

  def test_matched_analyses_take_no_label_layout (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      if (analysis['input'] == 'matched'):
        self.assertEqual (analysis['layouts'], ('columns', 'rows'), command)

  def test_option_args_of_ttestpaired (self):
    self.assertEqual (octave_stats.option_args ('TtestPaired', {}),
                      [{'type': 'string', 'value': 'both'},
                       {'type': 'number', 'value': 0.05}])

  def test_option_args_of_signrank (self):
    self.assertEqual (octave_stats.option_args ('SignRank', {}),
                      [{'type': 'string', 'value': 'auto'},
                       {'type': 'string', 'value': 'both'},
                       {'type': 'number', 'value': 0.05}])

  def test_option_args_of_friedman (self):
    self.assertEqual (octave_stats.option_args ('Friedman', {}),
                      [{'type': 'string', 'value': 'holm'},
                       {'type': 'number', 'value': 0.05}])

  def test_matched_refusal_names_measurements (self):
    self.assertIn ('measurement names',
                   octave_stats.allowed ('columns', 'matched'))

  def test_group_refusal_names_groups (self):
    self.assertIn ('group names', octave_stats.allowed ('columns'))

  def test_two_group_tests_take_every_layout (self):
    for command in ('Ttest2', 'Ranksum', 'VarTestN'):
      self.assertEqual (octave_stats.ANALYSES[command]['layouts'],
                        octave_stats.BY, command)


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


class NumbersOption (unittest.TestCase):

  OPTION = {'name': 'levels', 'kind': 'numbers', 'label': 'Levels per factor:',
            'hint': 'One number per factor.',
            'accepts': 'one whole number per factor, each 2 or more',
            'minimum': 1.0, 'maximum': 1000.0, 'whole': True,
            'default': '2 3 3'}

  def test_typed_list (self):
    self.assertEqual (octave_stats.option_numbers (self.OPTION, '2 3 3'),
                      [2.0, 3.0, 3.0])

  def test_commas_accepted (self):
    self.assertEqual (octave_stats.option_numbers (self.OPTION, '2, 3'),
                      [2.0, 3.0])

  def test_fraction_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.option_numbers (self.OPTION, '2 2.5')
    self.assertEqual (str (raised.exception),
                      'the levels per factor must be one whole number per '
                      'factor, each 2 or more.')

  def test_empty_refused (self):
    with self.assertRaises (ValueError):
      octave_stats.option_numbers (self.OPTION, '   ')

  def test_reaches_octave_as_a_range (self):
    args = octave_stats.option_args ('FullFactorial', {'levels': '2 3'})
    self.assertEqual ((args[0]['rows'], args[0]['cols'], args[0]['cells']),
                      (1, 2, [{'kind': 'number', 'value': 2.0},
                              {'kind': 'number', 'value': 3.0}]))

  def test_whole_number_option (self):
    args = octave_stats.option_args ('TwoLevelFactorial', {'factors': '4'})
    self.assertEqual (args, [{'type': 'number', 'value': 4.0}])

  def test_whole_number_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.option_args ('TwoLevelFactorial', {'factors': '4.5'})
    self.assertEqual (str (raised.exception),
                      'the factors must be a whole number from 1 to 15.')


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


# The menu runs its analyses with or without a sandbox, so these run wherever
# Octave does, as the menu's own server does
@unittest.skipUnless (octave_core.octave_problem () is None,
                      'no Octave on this machine')
class AnalysesInOctave (unittest.TestCase):

  @classmethod
  def setUpClass (cls):
    cls.runner = octave_core.Server (
      {'folders': [os.path.join (ROOT, 'octave')],
       'packages': [octave_stats.PACKAGE], 'memory': 2, 'tmp': 2,
       'seconds': 60}, sandbox_only = False)

  @classmethod
  def tearDownClass (cls):
    cls.runner.stop ()

  def run_analysis (self, rows, by, command = 'KruskalWallis', options = {}):
    analysis = octave_stats.ANALYSES[command]
    args = octave_stats.option_args (command, options)
    if (analysis['input'] != 'none'):
      args = (octave_stats.analysis_args (rows, by, 0, 0, analysis['input'])
              + args)
    return octave_stats.results (self.runner.call (analysis['function'], args))

  def titled (self, command):
    """The title the registry gives COMMAND, which the analysis writes into
    the first cell of its results; the dialog and the sheet say the same
    thing or one of them is wrong."""
    return octave_stats.ANALYSES[command]['title']

  MATCHED = (('Before', 'After'), (12.0, 14.0), (15.0, 18.0), (11.0, 13.0),
             (14.0, 15.0), (13.0, 16.0), (16.0, 17.0), (12.0, 15.0),
             (15.0, 19.0))

  def test_anova_reaches_cells (self):
    table = self.run_analysis (((1.0, 4.0, 7.0), (2.0, 5.0, 9.0),
                                (3.0, 6.0, 8.0)), 'columns', 'Anova1')
    self.assertEqual ((table[0][0], table[3][:3]),
                      (self.titled ('Anova1'), ('Column 1', 3.0, 2.0)))

  def test_results_reach_cells (self):
    table = self.run_analysis (((1.0, 4.0, 7.0), (2.0, 5.0, 8.0),
                                (3.0, '', 9.0)), 'columns')
    self.assertEqual (table[0][0], self.titled ('KruskalWallis'))
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

  def test_ttest2_reaches_cells (self):
    table = self.run_analysis (((1.0, 3.0), (2.0, 5.0), (3.0, 7.0),
                                (4.0, 9.0), (5.0, 11.0)), 'columns', 'Ttest2')
    self.assertEqual (table[0][0], self.titled ('Ttest2'))
    self.assertEqual (table[8][:2], ('Column 1', 'Column 2'))
    self.assertEqual (table[8][3], -4.0)

  def test_ranksum_reaches_cells (self):
    table = self.run_analysis (((1.0, 3.0), (2.0, 5.0), (4.0, 7.0),
                                (6.0, 9.0), (8.0, 11.0)), 'columns', 'Ranksum')
    self.assertEqual (table[0][0], self.titled ('Ranksum'))
    self.assertEqual (table[7][:5], ('Group', 'Group', 'U', 'z', 'p-value'))

  def test_exact_ranksum_has_no_z (self):
    table = self.run_analysis (((1.0, 3.0), (2.0, 5.0), (4.0, 7.0),
                                (6.0, 9.0), (8.0, 11.0)), 'columns', 'Ranksum')
    self.assertTrue (math.isnan (table[8][3]))

  def test_equal_variances_reaches_cells (self):
    table = self.run_analysis (((1.0, 3.0, 2.0), (2.0, 5.0, 9.0),
                                (4.0, 7.0, 3.0), (6.0, 9.0, 14.0)),
                               'columns', 'VarTestN')
    self.assertEqual (table[0][0], self.titled ('VarTestN'))
    self.assertEqual (table[7][0], "Bartlett's test (alpha 0.05)")
    self.assertEqual ([line[0] for line in table[8:11]],
                      ['Statistic', 'DoF', 'p-value'])

  def test_two_groups_add_the_variance_ratio (self):
    table = self.run_analysis (((1.0, 3.0), (2.0, 5.0), (4.0, 7.0),
                                (6.0, 9.0), (8.0, 12.0)), 'columns',
                               'VarTestN')
    self.assertEqual (table[11][0], 'Ratio of variances (alpha 0.05)')

  def test_three_groups_refused_by_a_two_group_test (self):
    with self.assertRaises (RuntimeError) as raised:
      self.run_analysis (((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)), 'columns',
                         'Ttest2')
    self.assertEqual (
      octave_stats.reason (str (raised.exception), 'octave_calc_ttest2'),
      'the input range must hold exactly two groups.')

  def test_paired_ttest_reaches_cells (self):
    table = self.run_analysis (self.MATCHED, 'columns', 'TtestPaired')
    self.assertEqual (table[0][0], self.titled ('TtestPaired'))
    self.assertEqual ([line[0] for line in table[3:6]],
                      ['Before', 'After', 'Difference'])
    self.assertEqual (table[9][:2], ('Before', 'After'))

  def test_signrank_reaches_cells (self):
    table = self.run_analysis (self.MATCHED, 'columns', 'SignRank')
    self.assertEqual (table[0][0], self.titled ('SignRank'))
    self.assertEqual (table[7][0], 'Ranks (two-sided, exact, alpha 0.05)')

  def test_signtest_reaches_cells (self):
    table = self.run_analysis (self.MATCHED, 'columns', 'SignTest')
    self.assertEqual (table[0][0], self.titled ('SignTest'))
    self.assertEqual (table[8][2], 'Differences that are not zero')

  def test_friedman_reaches_cells (self):
    rows = tuple (line + (extra,) for line, extra in
                  zip (self.MATCHED, ('Later', 13.0, 16.0, 12.0, 13.0, 15.0,
                                      18.0, 14.0, 17.0)))
    table = self.run_analysis (rows, 'columns', 'Friedman')
    self.assertEqual (table[0][0], self.titled ('Friedman'))
    self.assertEqual ([line[0] for line in table[3:6]],
                      ['Before', 'After', 'Later'])
    self.assertEqual (table[7][:6], ('Source', 'SS', 'DoF', 'MS', 'Chi-sq',
                                     'Prob>Chi-sq'))

  def test_dropped_subject_is_reported (self):
    rows = self.MATCHED + ((20.0, ''),)
    table = self.run_analysis (rows, 'columns', 'TtestPaired')
    self.assertEqual (table[2][0],
                      'One subject was left out for a missing measurement.')

  def test_matched_refusal_names_the_cell (self):
    rows = (('Before', 'After'), (12.0, 'oops'), (15.0, 18.0))
    with self.assertRaises (ValueError) as raised:
      self.run_analysis (rows, 'columns', 'TtestPaired')
    self.assertEqual (
      str (raised.exception),
      'B2 holds the text "oops"; the input range may hold measurement names '
      'in its first row, then numbers and empty cells only.')

  FACTORIAL = (('Yield', 'Fert', 'Var'),
               (52.0, 'lo', 'x'), (60.0, 'lo', 'y'), (63.0, 'hi', 'x'),
               (71.0, 'hi', 'y'), (55.0, 'lo', 'x'), (62.0, 'lo', 'y'),
               (66.0, 'hi', 'x'), (74.0, 'hi', 'y'))

  def test_two_way_anova_reaches_cells (self):
    table = self.run_analysis (self.FACTORIAL, 'data-labels', 'Anova2')
    self.assertEqual (table[0][0], self.titled ('Anova2'))
    self.assertEqual (table[2][:3], ('Fert', 'Var', 'Count'))
    self.assertEqual (table[8][:6], ('Source', 'SS', 'DoF', 'MS', 'F',
                                     'Prob>F'))
    self.assertEqual ([line[0] for line in table[9:14]],
                      ['Fert', 'Var', 'Fert:Var', 'Error', 'Total'])

  def test_two_way_anova_names_its_comparisons (self):
    table = self.run_analysis (self.FACTORIAL, 'data-labels', 'Anova2')
    self.assertEqual (table[15][0],
                      'Multiple comparisons (holm, alpha 0.05) of Fert')

  def test_interaction_without_replication_refused (self):
    rows = (('Yield', 'Fert', 'Var'), (52.0, 'lo', 'x'), (60.0, 'lo', 'y'),
            (63.0, 'hi', 'x'), (71.0, 'hi', 'y'))
    with self.assertRaises (RuntimeError) as raised:
      self.run_analysis (rows, 'data-labels', 'Anova2')
    self.assertEqual (
      octave_stats.reason (str (raised.exception), 'octave_calc_anova2'),
      'every combination of Fert and Var holds at most one value, so the '
      'interaction cannot be told apart from the error; take the two effects '
      'as adding instead.')

  SAMPLE = (('Yield',), (4.2,), (5.1,), (3.8,), (6.0,), (4.9,), (5.5,),
            (4.1,), (5.8,), (4.6,), (5.2,), (3.9,), (6.3,), (4.4,), (5.0,),
            (4.8,), (5.3,), (4.7,), (5.6,), (4.0,), (5.9,), (4.3,), (5.4,),
            (4.5,), (5.7,), (4.85,))

  def test_one_sample_ttest_reaches_cells (self):
    table = self.run_analysis (self.SAMPLE, 'columns', 'Ttest1')
    self.assertEqual (table[0][0], self.titled ('Ttest1'))
    self.assertEqual (table[3][:2], ('Yield', 25.0))
    self.assertEqual (table[5][0], 'Difference from 0 (two-sided, alpha 0.05)')

  def test_normality_reaches_cells (self):
    table = self.run_analysis (self.SAMPLE, 'columns', 'Normality')
    self.assertEqual (table[0][0], self.titled ('Normality'))
    self.assertEqual ([line[0] for line in table[-4:]],
                      ['Anderson-Darling', 'Lilliefors', 'Jarque-Bera',
                       'Shapiro-Wilk'])

  def test_too_many_bins_are_refused_by_name (self):
    with self.assertRaises (RuntimeError) as raised:
      self.run_analysis (self.SAMPLE, 'columns', 'Chi2gof')
    self.assertIn ('leave no degrees of freedom',
                   octave_stats.reason (str (raised.exception),
                                        'octave_calc_chi2gof'))

  def test_goodness_of_fit_reaches_cells (self):
    table = self.run_analysis (self.SAMPLE, 'columns', 'Chi2gof',
                               {'nbins': '6'})
    self.assertEqual (table[0][0], self.titled ('Chi2gof'))
    self.assertEqual ([line[0] for line in table[6:11]],
                      ['Statistic', 'DoF', 'p-value', 'Bins asked for',
                       'Bins counted'])

  def test_fitdist_reaches_cells (self):
    table = self.run_analysis (self.SAMPLE, 'columns', 'Fitdist')
    self.assertEqual (table[0][0], self.titled ('Fitdist'))
    self.assertEqual (table[6][:4], ('Parameter', 'Estimate', 'Lower bound',
                                     'Upper bound'))
    self.assertEqual ([line[0] for line in table[7:9]], ['mu', 'sigma'])

  def test_outliers_reach_cells (self):
    rows = self.SAMPLE + ((18.4,),)
    table = self.run_analysis (rows, 'columns', 'Isoutlier')
    self.assertEqual (table[0][0], self.titled ('Isoutlier'))
    self.assertEqual (table[6][:3], ('Row', 'Value', 'Beyond the bound'))
    self.assertEqual (table[7][:2], (26.0, 18.4))

  def test_the_fitted_distributions_are_the_ones_fitdist_takes (self):
    """The registry names them so the dialog can list them without asking
    Octave; this is what catches a distribution gained or lost upstream."""
    listed = self.runner.call ('fitdist', [])
    named = tuple (line[0] for line in octave_core.output_rows (listed[0]))
    self.assertEqual (named, octave_stats.FITTED)

  def test_random_numbers_reach_cells (self):
    table = self.run_analysis ((), 'columns', 'RandomNumbers',
                               {'params': '5 2', 'nrows': '3', 'ncols': '4',
                                'seed': '7'})
    self.assertEqual (table[0][0], self.titled ('RandomNumbers'))
    self.assertEqual ([line[0] for line in table[2:7]],
                      ['Distribution', 'mu', 'sigma', 'Size', 'Seed'])
    self.assertEqual (len (table), 11)

  def test_a_seed_that_was_not_given_is_still_written (self):
    table = self.run_analysis ((), 'columns', 'RandomNumbers',
                               {'params': '5 2', 'nrows': '2', 'ncols': '2'})
    self.assertEqual (table[6][0], 'Seed')
    self.assertTrue (isinstance (table[6][1], float))

  def test_the_drawn_distributions_are_the_ones_makedist_takes (self):
    """Every distribution the dialog offers must be one makedist builds
    from a number per parameter; the three it cannot are left out."""
    listed = self.runner.call ('makedist', [])
    named = set (line[0] for line in octave_core.output_rows (listed[0]))
    offered = set (name for name, unused in octave_stats.DRAWN)
    self.assertEqual (named - offered,
                      {'Kernel', 'Multinomial', 'PiecewiseLinear'})

  def test_refusal_names_no_function (self):
    with self.assertRaises (RuntimeError) as raised:
      self.run_analysis (((1.0,), (2.0,)), 'columns')
    self.assertEqual (
      octave_stats.reason (str (raised.exception),
                           'octave_calc_kruskalwallis'),
      'the input range holds fewer than two groups.')


if (__name__ == '__main__'):
  unittest.main ()
