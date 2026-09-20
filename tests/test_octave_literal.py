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

"""Tests for octave_literal.  From the repository root:

  python3 -m unittest discover tests

The count of a typed range is held against the real Octave, since a step it
cannot hold exactly decides whether the last element is there.
"""

import math
import os
import sys
import unittest

ROOT = os.path.dirname (os.path.dirname (os.path.abspath (__file__)))
sys.path.insert (0, os.path.join (ROOT, 'python'))

import octave_core
import octave_literal
import octave_stats


class Numbers (unittest.TestCase):

  def test_whole (self):
    self.assertEqual (octave_literal.parse ('3'),
                      {'type': 'number', 'value': 3.0})

  def test_negative_fraction (self):
    self.assertEqual (octave_literal.parse (' -2.5 ')['value'], -2.5)

  def test_exponent (self):
    self.assertEqual (octave_literal.parse ('1e3')['value'], 1000.0)

  def test_infinity_either_sign (self):
    self.assertEqual ((octave_literal.parse ('Inf')['value'],
                       octave_literal.parse ('-inf')['value']),
                      (float ('inf'), float ('-inf')))

  def test_not_a_number (self):
    self.assertTrue (math.isnan (octave_literal.parse ('NaN')['value']))


class Text (unittest.TestCase):

  def test_single_quotes (self):
    self.assertEqual (octave_literal.parse ("'abc'"),
                      {'type': 'string', 'value': 'abc'})

  def test_double_quotes_hold_spaces (self):
    self.assertEqual (octave_literal.parse ('"a b"')['value'], 'a b')

  def test_two_quotes_stand_for_one (self):
    self.assertEqual (octave_literal.parse ("'it''s'")['value'], "it's")

  def test_a_quote_inside_is_not_text (self):
    with self.assertRaises (ValueError):
      octave_literal.parse ("'a'b'")


class Logicals (unittest.TestCase):

  def test_true (self):
    self.assertEqual (octave_literal.parse ('true'),
                      {'type': 'logical', 'value': True})

  def test_false_in_any_case (self):
    self.assertEqual (octave_literal.parse ('FALSE')['value'], False)


class Matrices (unittest.TestCase):

  def test_empty (self):
    self.assertEqual (octave_literal.parse ('[]'),
                      {'type': 'range', 'rows': 0, 'cols': 0, 'cells': []})

  def test_rows_and_columns (self):
    arg = octave_literal.parse ('[1, 2; 3, 4]')
    self.assertEqual ((arg['rows'], arg['cols']), (2, 2))
    self.assertEqual ([cell['value'] for cell in arg['cells']],
                      [1.0, 2.0, 3.0, 4.0])

  def test_spaces_separate_as_commas_do (self):
    self.assertEqual (octave_literal.parse ('[1 2 3]')['cols'], 3)

  def test_a_column_is_semicolons (self):
    arg = octave_literal.parse ('[1; 2; 3]')
    self.assertEqual ((arg['rows'], arg['cols']), (3, 1))

  def test_ragged_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_literal.parse ('[1, 2; 3]')
    self.assertEqual (str (raised.exception),
                      'every row of a matrix must hold the same count of '
                      'numbers.')

  def test_a_range_inside_is_spread_out (self):
    arg = octave_literal.parse ('[1:5, 10, 20:5:40]')
    self.assertEqual (arg['cols'], 11)
    self.assertEqual (arg['cells'][-1]['value'], 40.0)


class Ranges (unittest.TestCase):

  def test_whole_step (self):
    self.assertEqual (octave_literal.parse ('1:5')['cols'], 5)

  def test_named_step (self):
    self.assertEqual (octave_literal.parse ('1:0.5:3')['cols'], 5)

  def test_backwards (self):
    self.assertEqual (octave_literal.parse ('1:-0.25:0')['cols'], 5)

  def test_empty_where_it_never_arrives (self):
    self.assertEqual (octave_literal.parse ('5:1')['rows'], 0)

  def test_too_many_refused_by_count (self):
    with self.assertRaises (ValueError) as raised:
      octave_literal.parse ('1:0.1:1e9')
    self.assertIn ('the most a field may hold is 1000000',
                   str (raised.exception))


class Refusals (unittest.TestCase):
  """What is not a literal.  A field that holds none of these is read as a
  range reference instead, so the message says what a literal is and never
  guesses at what was meant."""

  def test_a_transpose_names_the_column (self):
    with self.assertRaises (ValueError) as raised:
      octave_literal.parse ("[1:5]'")
    self.assertIn ('Type a column with semicolons', str (raised.exception))

  def test_a_transposed_number_too (self):
    with self.assertRaises (ValueError):
      octave_literal.parse ("5'")

  def test_parentheses_named (self):
    with self.assertRaises (ValueError) as raised:
      octave_literal.parse ('sin(2)')
    self.assertIn ('no parentheses', str (raised.exception))

  def test_a_name_is_not_a_literal (self):
    with self.assertRaises (ValueError):
      octave_literal.parse ('pi')

  def test_an_expression_is_not_a_literal (self):
    with self.assertRaises (ValueError):
      octave_literal.parse ('2 + 2')

  def test_a_reference_is_not_a_literal (self):
    """It is a range, which the caller resolves once this has refused it."""
    for reference in ('A1:B10', 'Sheet2.C3'):
      with self.assertRaises (ValueError):
        octave_literal.parse (reference)

  def test_empty (self):
    with self.assertRaises (ValueError) as raised:
      octave_literal.parse ('   ')
    self.assertEqual (str (raised.exception), 'it is empty.')


class Pairs (unittest.TestCase):

  def test_names_and_values (self):
    args = octave_literal.pairs ("{'Name', 2.3, 'Next', [2, 3]}")
    self.assertEqual ([arg['type'] for arg in args],
                      ['string', 'number', 'string', 'range'])

  def test_odd_count_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_literal.pairs ("{'a', 1, 'b'}")
    self.assertIn ('even in number', str (raised.exception))

  def test_a_name_must_be_text (self):
    with self.assertRaises (ValueError) as raised:
      octave_literal.pairs ('{1, 2}')
    self.assertIn ('must be text in quotes', str (raised.exception))

  def test_a_nested_cell_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_literal.pairs ("{'a', {1}}")
    self.assertEqual (str (raised.exception),
                      'the value of a pair cannot itself be a cell.')

  def test_a_comma_inside_text_does_not_split (self):
    args = octave_literal.pairs ("{'a, b', 1}")
    self.assertEqual (args[0]['value'], 'a, b')

  def test_not_a_cell_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_literal.pairs ("'Name', 1")
    self.assertIn ('typed as a cell', str (raised.exception))


class CountedInOctave (unittest.TestCase):
  """A range is counted here and must be counted as Octave counts it, a step
  it cannot hold exactly otherwise dropping the last element."""

  SPREADS = ((0.0, 0.1, 1.0), (0.0, 0.1, 0.7), (0.0, 0.1, 0.3),
             (1.0, 0.2, 2.0), (0.0, 1.0 / 3.0, 1.0), (1.0, -0.25, 0.0),
             (0.0, 0.7, 10.0), (2.0, 3.0, 2.0), (1.0, 1.0, 5.0),
             (5.0, 1.0, 1.0))

  @classmethod
  def setUpClass (cls):
    cls.runner = octave_core.Server (
      {'folders': [os.path.join (ROOT, 'tests', 'functions')],
       'packages': [], 'memory': 2, 'tmp': 2, 'seconds': 60},
      sandbox_only = False)

  @classmethod
  def tearDownClass (cls):
    cls.runner.stop ()

  def test_counted_as_octave_counts (self):
    for first, step, last in self.SPREADS:
      said = self.runner.call ('octave_calc_spread',
                               [{'type': 'number', 'value': first},
                                {'type': 'number', 'value': step},
                                {'type': 'number', 'value': last}])
      self.assertEqual (octave_literal.counted (first, step, last),
                        int (octave_core.output_rows (said[0])[0][0]),
                        '%g:%g:%g' % (first, step, last))


if (__name__ == '__main__'):
  unittest.main ()
