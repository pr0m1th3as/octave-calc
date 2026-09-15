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

"""Tests for octave_core.  From the repository root:

  python3 -m unittest discover tests

The tests that run Octave are skipped when no interpreter is on PATH.
"""

import os
import sys
import types
import unittest

sys.path.insert (0, os.path.join (os.path.dirname (os.path.dirname (
  os.path.abspath (__file__))), 'python'))

import octave_core


def kind (content = 'VALUE', result = 0, error = 0, value = 1.0, text = '1',
          format_type = 16, format_string = 'General'):
  return octave_core.cell_kind (content, result, error, value, text,
                                format_type, format_string)


def text (value):
  return {'kind': 'text', 'value': value}


def number (value):
  return {'kind': 'number', 'value': value}


EMPTY = {'kind': 'empty'}


class CellKind (unittest.TestCase):

  def test_empty (self):
    self.assertEqual (kind ('EMPTY', value = 0.0, text = ''), EMPTY)

  def test_number (self):
    self.assertEqual (kind (value = 2.5), number (2.5))

  def test_text (self):
    self.assertEqual (kind ('TEXT', text = 'abc'), text ('abc'))

  def test_formula_text (self):
    self.assertEqual (kind ('FORMULA', result = 2, text = 'a'), text ('a'))

  def test_formula_number (self):
    self.assertEqual (kind ('FORMULA', result = 1, value = 3.0), number (3.0))

  def test_error_named_from_code (self):
    self.assertEqual (kind ('FORMULA', result = 4, error = 532,
                            text = '...', format_type = 2),
                      {'kind': 'error', 'value': '#DIV/0!'})

  def test_logical (self):
    self.assertEqual (kind (value = 0.0, format_type = 1024),
                      {'kind': 'logical', 'value': False})

  def test_date (self):
    self.assertEqual (kind (value = 46279.0, format_type = 2),
                      {'kind': 'date', 'value': 46279.0})

  def test_user_defined_date (self):
    self.assertEqual (kind (value = 46279.0, format_type = 3),
                      {'kind': 'date', 'value': 46279.0})

  def test_datetime (self):
    self.assertEqual (kind (value = 46279.5, format_type = 6),
                      {'kind': 'datetime', 'value': 46279.5})

  def test_time_of_day (self):
    self.assertEqual (kind (value = 0.5, format_type = 4,
                            format_string = 'HH:MM:SS AM/PM'),
                      {'kind': 'time', 'value': 0.5})

  def test_elapsed_time (self):
    self.assertEqual (kind (value = 1.5, format_type = 4,
                            format_string = '[HH]:MM:SS'),
                      {'kind': 'duration', 'value': 1.5})

  def test_duration_type (self):
    self.assertEqual (kind (value = 1.5, format_type = 8196,
                            format_string = 'HH:MM:SS'),
                      {'kind': 'duration', 'value': 1.5})

  def test_currency (self):
    self.assertEqual (kind (value = 4.0, format_type = 8), number (4.0))


class PlainRange (unittest.TestCase):

  def test_shape (self):
    arg = octave_core.plain_range (((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))
    self.assertEqual ((arg['type'], arg['rows'], arg['cols'],
                       len (arg['cells'])), ('range', 2, 3, 6))

  def test_row_order (self):
    arg = octave_core.plain_range (((1.0, 2.0), (3.0, 4.0)))
    self.assertEqual ([c['value'] for c in arg['cells']],
                      [1.0, 2.0, 3.0, 4.0])

  def test_empty_text_is_empty (self):
    arg = octave_core.plain_range ((('', 'a'),))
    self.assertEqual (arg['cells'], [EMPTY, text ('a')])

  def test_scalar (self):
    arg = octave_core.plain_range (7.0)
    self.assertEqual ((arg['rows'], arg['cols']), (1, 1))


class ErrorName (unittest.TestCase):

  def test_named (self):
    self.assertEqual (octave_core.error_name (532), '#DIV/0!')

  def test_not_available (self):
    self.assertEqual (octave_core.error_name (32767), '#N/A')

  def test_unnamed (self):
    self.assertEqual (octave_core.error_name (504), 'Err:504')


DATES = [[{'kind': 'date', 'value': 45658.0}], [EMPTY]]
KEY = octave_core.range_key ('data', '$Sheet1.$A$1:$A$2', DATES)
DIGEST = KEY.rsplit ('|', 1)[1]


def no_key (key):
  raise AssertionError ('no key expected')


def keys (table):
  """A resolver answering from TABLE, a dict of key to (column, row, rows)."""
  return lambda key: table[key]


class RangeMode (unittest.TestCase):

  def test_omitted (self):
    self.assertEqual (octave_core.range_mode (None), 'data')

  def test_empty_text (self):
    self.assertEqual (octave_core.range_mode (''), 'data')

  def test_any_capitals (self):
    self.assertEqual (octave_core.range_mode ('Pairs'), 'pairs')

  def test_unknown (self):
    with self.assertRaisesRegex (ValueError,
                                 r'^mode must be "data" or "pairs"\.$'):
      octave_core.range_mode ('options')

  def test_not_text (self):
    with self.assertRaisesRegex (ValueError,
                                 r'^mode must be "data" or "pairs"\.$'):
      octave_core.range_mode (1.0)


class RangeKey (unittest.TestCase):

  def test_prefix (self):
    self.assertTrue (KEY.startswith ('octrange|data|$Sheet1.$A$1:$A$2|'))

  def test_full_digest (self):
    self.assertEqual (len (DIGEST), 40)

  def test_contents_change_key (self):
    rows = [[{'kind': 'date', 'value': 45659.0}], [EMPTY]]
    self.assertNotEqual (
      octave_core.range_key ('data', '$Sheet1.$A$1:$A$2', rows), KEY)

  def test_mode_changes_key (self):
    self.assertNotEqual (
      octave_core.range_key ('pairs', '$Sheet1.$A$1:$A$2', DATES), KEY)

  def test_parts (self):
    self.assertEqual (octave_core.key_parts (KEY),
                      ('data', '$Sheet1.$A$1:$A$2'))

  def test_bar_in_sheet_name (self):
    key = octave_core.range_key ('pairs', '$\'a|b\'.$A$1', DATES)
    self.assertEqual (octave_core.key_parts (key), ('pairs', '$\'a|b\'.$A$1'))

  def test_no_mode (self):
    self.assertIsNone (octave_core.key_parts (
      'octrange|$Sheet1.$A$1:$A$2|' + DIGEST))

  def test_unknown_mode (self):
    self.assertIsNone (octave_core.key_parts (
      'octrange|options|$Sheet1.$A$1:$A$2|' + DIGEST))

  def test_bad_digest (self):
    self.assertIsNone (octave_core.key_parts (
      'octrange|data|$Sheet1.$A$1:$A$2|00000000'))


class BuildArgs (unittest.TestCase):

  def test_none (self):
    self.assertEqual (octave_core.build_args ((), no_key), [])

  def test_literals (self):
    built = octave_core.build_args ((2.0, 'omitnan', True), no_key)
    self.assertEqual (built, [{'type': 'number', 'value': 2.0},
                              {'type': 'string', 'value': 'omitnan'},
                              {'type': 'logical', 'value': True}])

  def test_trailing_omitted_dropped (self):
    self.assertEqual (len (octave_core.build_args ((2.0, None, None),
                                                   no_key)), 1)

  def test_omitted_between (self):
    with self.assertRaisesRegex (ValueError, r'^argument 2 is empty\.$'):
      octave_core.build_args ((2.0, None, 3.0), no_key)

  def test_range_by_value (self):
    built = octave_core.build_args ((((1.0, 2.0),),), no_key)
    self.assertEqual ((built[0]['type'], built[0]['cols']), ('range', 2))

  def test_key_in_any_position (self):
    built = octave_core.build_args ((2.0, KEY), keys ({KEY: (0, 0, DATES)}))
    self.assertEqual (built[1], octave_core.range_arg (DATES))

  def test_key_with_error_cell (self):
    rows = [[{'kind': 'error', 'value': '#DIV/0!'}]]
    with self.assertRaisesRegex (ValueError,
                                 r'^C5 holds the error #DIV/0!\.$'):
      octave_core.build_args ((KEY,), keys ({KEY: (2, 4, rows)}))

  def test_key_without_mode (self):
    key = 'octrange|$Sheet1.$A$1:$A$2|' + DIGEST
    with self.assertRaisesRegex (ValueError, r'is not an OCTRANGE key\.$'):
      octave_core.build_args ((key,), no_key)

  def test_message_refused (self):
    with self.assertRaisesRegex (ValueError, r'^no Octave\.$'):
      octave_core.build_args (('octave-calc: no Octave.',), no_key)


OPTIONS = [[text ('Alpha'), number (0.5)],
           [EMPTY, EMPTY],
           [text ('Standardize'), {'kind': 'logical', 'value': False}]]
PAIRS = octave_core.range_key ('pairs', '$Sheet1.$G$1:$H$3', OPTIONS)


class Pairs (unittest.TestCase):

  def expand (self, rows, table = None):
    key = octave_core.range_key ('pairs', '$Sheet1.$G$1:$H$9', rows)
    lookup = dict (table or {})
    lookup[key] = (6, 0, rows)
    return octave_core.build_args ((1.0, key), keys (lookup))

  def test_expanded_in_place (self):
    built = octave_core.build_args ((1.0, PAIRS, 2.0),
                                    keys ({PAIRS: (6, 0, OPTIONS)}))
    self.assertEqual (built, [{'type': 'number', 'value': 1.0},
                              {'type': 'string', 'value': 'Alpha'},
                              {'type': 'number', 'value': 0.5},
                              {'type': 'string', 'value': 'Standardize'},
                              {'type': 'logical', 'value': False},
                              {'type': 'number', 'value': 2.0}])

  def test_text_value (self):
    built = self.expand ([[text ('Kernel'), text ('epanechnikov')]])
    self.assertEqual (built[2], {'type': 'string', 'value': 'epanechnikov'})

  def test_date_value_keeps_kind (self):
    date = {'kind': 'date', 'value': 45658.0}
    built = self.expand ([[text ('Start'), date]])
    self.assertEqual (built[2], octave_core.range_arg ([[date]]))

  def test_vector_value_from_key (self):
    vector = [[number (0.1)], [number (0.2)], [number (0.3)]]
    key = octave_core.range_key ('data', '$Sheet1.$J$1:$J$3', vector)
    built = self.expand ([[text ('Lambda'), text (key)]],
                         {key: (9, 0, vector)})
    self.assertEqual (built[2], octave_core.range_arg (vector))

  def test_pairs_key_as_value (self):
    key = octave_core.range_key ('pairs', '$Sheet1.$J$1:$K$1', OPTIONS)
    with self.assertRaisesRegex (ValueError,
                                 r'^H1 holds a "pairs" range; an option '
                                 r'value takes a "data" range\.$'):
      self.expand ([[text ('Lambda'), text (key)]], {key: (9, 0, OPTIONS)})

  def test_blank_rows_only (self):
    self.assertEqual (self.expand ([[EMPTY, EMPTY]]),
                      [{'type': 'number', 'value': 1.0}])

  def test_name_without_value (self):
    with self.assertRaisesRegex (ValueError,
                                 r'^G2 names the option "CV" but H2 holds '
                                 r'no value\.$'):
      self.expand ([[text ('Alpha'), number (0.5)], [text ('CV'), EMPTY]])

  def test_name_not_text (self):
    with self.assertRaisesRegex (ValueError,
                                 r'^G1 holds an option name that is not '
                                 r'text\.$'):
      self.expand ([[number (3.0), number (0.5)]])

  def test_three_columns (self):
    with self.assertRaisesRegex (ValueError,
                                 r'^the "pairs" range at G1 has 3 columns; '
                                 r'it needs two, name then value\.$'):
      self.expand ([[text ('Alpha'), number (0.5), number (1.0)]])

  def test_error_cell (self):
    with self.assertRaisesRegex (ValueError, r'^H1 holds the error #N/A\.$'):
      self.expand ([[text ('Alpha'), {'kind': 'error', 'value': '#N/A'}]])

  def test_message_value (self):
    with self.assertRaisesRegex (ValueError, r'^no Octave\.$'):
      self.expand ([[text ('Alpha'), text ('octave-calc: no Octave.')]])


class CellName (unittest.TestCase):

  def test_first (self):
    self.assertEqual (octave_core.cell_name (0, 0), 'A1')

  def test_last_single_letter (self):
    self.assertEqual (octave_core.cell_name (25, 9), 'Z10')

  def test_first_two_letters (self):
    self.assertEqual (octave_core.cell_name (26, 0), 'AA1')

  def test_carry (self):
    self.assertEqual (octave_core.cell_name (52, 0), 'BA1')

  def test_first_three_letters (self):
    self.assertEqual (octave_core.cell_name (702, 0), 'AAA1')


class RefuseErrors (unittest.TestCase):

  def test_clean (self):
    self.assertIsNone (octave_core.refuse_errors ([[number (1.0)]], 0, 0))

  def test_names_cell_on_sheet (self):
    rows = [[number (1.0)], [{'kind': 'error', 'value': '#DIV/0!'}]]
    self.assertEqual (octave_core.refuse_errors (rows, 1, 2),
                      'B4 holds the error #DIV/0!.')


class KeptRanges (unittest.TestCase):

  def tearDown (self):
    octave_core.clear ()

  def test_recall (self):
    octave_core.remember_range (KEY, 0, 0, DATES)
    self.assertEqual (octave_core.recall_range (KEY), (0, 0, DATES))

  def test_clear_forgets (self):
    octave_core.remember_range (KEY, 0, 0, DATES)
    octave_core.clear ()
    self.assertIsNone (octave_core.recall_range (KEY))


class IsoDate (unittest.TestCase):

  def test_padding (self):
    date = types.SimpleNamespace (Year = 1904, Month = 1, Day = 1)
    self.assertEqual (octave_core.iso_date (date), '1904-01-01')


class Call (unittest.TestCase):

  def test_refuses_code (self):
    self.assertEqual (octave_core.call ('disp (1)', []),
                      (('octave-calc: "disp (1)" is not a function name.',),))


@unittest.skipUnless (octave_core.octave (), 'no Octave interpreter on PATH')
class Run (unittest.TestCase):

  def test_empty_cell_is_nan (self):
    data = octave_core.range_arg ([
      [number (1.0), number (2.0), number (3.0)],
      [number (4.0), EMPTY, number (6.0)]])
    args = [data] + octave_core.build_args ((2.0, 'omitnan'), no_key)
    self.assertEqual (octave_core.run ('mean', args), ((2.0,), (5.0,)))

  def test_logical_range (self):
    data = octave_core.range_arg ([[{'kind': 'logical', 'value': True},
                                    {'kind': 'logical', 'value': False}]])
    self.assertEqual (octave_core.run ('class', [data]), (('logical',),))

  def test_text_range (self):
    data = octave_core.plain_range ((('a', ''),))
    self.assertEqual (octave_core.run ('class', [data]), (('cell',),))

  def test_pairs_reach_function_as_options (self):
    rows = [[text ('Endpoints'), number (0.0)]]
    key = octave_core.range_key ('pairs', '$Sheet1.$A$1:$B$1', rows)
    data = octave_core.plain_range (((1.0, 2.0, 3.0, 4.0),))
    args = [data] + octave_core.build_args ((3.0, key),
                                            keys ({key: (0, 0, rows)}))
    # Padding with 0 gives the ends (0+1+2)/3 and (3+4+0)/3; without the
    # option they would shrink to 1.5 and 3.5
    result = octave_core.run ('movmean', args)
    self.assertEqual ([round (v, 12) for v in result[0]],
                      [1.0, 2.0, 3.0, round (7.0 / 3, 12)])

  def test_error_reaches_caller (self):
    data = octave_core.plain_range (1.0)
    with self.assertRaisesRegex (RuntimeError, 'undefined'):
      octave_core.run ('octave_calc_no_such_function', [data])


if (__name__ == '__main__'):
  unittest.main ()
