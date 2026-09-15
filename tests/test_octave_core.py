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

The tests that run Octave do so in the real sandboxed devtools server, and are
skipped where no sandbox can run.  They need Linux, bwrap, prlimit, octave-cli
and the devtools package, and one of them the datatypes package.
"""

import math
import os
import struct
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

  def test_not_available_is_missing (self):
    self.assertEqual (kind ('FORMULA', result = 4, error = 32767,
                            text = '...'),
                      {'kind': 'empty', 'na': True})

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


class NumericTexts (unittest.TestCase):

  def test_texts_in_numbers (self):
    rows = octave_core.numeric_texts ([[number (1.0), text ('Inf')],
                                       [text ('-Inf'), EMPTY]])
    self.assertEqual (rows, [[number (1.0), number (float ('inf'))],
                             [number (float ('-inf')), EMPTY]])

  def test_nan_text (self):
    value = octave_core.numeric_texts ([[text ('NaN'), number (2.0)]])[0][0]
    self.assertTrue (value['kind'] == 'number' and math.isnan (value['value']))

  def test_any_capitals (self):
    rows = octave_core.numeric_texts ([[text ('INF'), number (2.0)]])
    self.assertEqual (rows[0][0], number (float ('inf')))

  def test_all_texts (self):
    rows = octave_core.numeric_texts ([[text ('Inf'), text ('-Inf')]])
    self.assertEqual (rows, [[number (float ('inf')),
                              number (float ('-inf'))]])

  def test_other_text_leaves_range (self):
    rows = [[text ('Inf'), text ('abc'), number (1.0)]]
    self.assertEqual (octave_core.numeric_texts (rows), rows)

  def test_date_leaves_range (self):
    rows = [[text ('Inf'), {'kind': 'date', 'value': 45658.0}]]
    self.assertEqual (octave_core.numeric_texts (rows), rows)


class Labels (unittest.TestCase):

  def test_same_sheet (self):
    self.assertEqual (octave_core.range_label (KEY, 'Sheet1'),
                      'A1:A2 (data)')

  def test_other_sheet (self):
    self.assertEqual (octave_core.range_label (KEY, 'Sheet2'),
                      'Sheet1.A1:A2 (data)')

  def test_quoted_sheet (self):
    key = octave_core.range_key ('pairs', "$'It''s here'.$G$1:$H$3", DATES)
    self.assertEqual (octave_core.range_label (key, "It's here"),
                      'G1:H3 (pairs)')

  def test_single_cell (self):
    key = octave_core.range_key ('data', '$Sheet1.$C$1', DATES)
    self.assertEqual (octave_core.range_label (key, 'Sheet1'), 'C1 (data)')

  def test_not_a_key (self):
    self.assertIsNone (octave_core.range_label ('abc', 'Sheet1'))

  def test_format_escapes_every_character (self):
    self.assertEqual (octave_core.label_format ('A1 (data)'),
                      'General;-General;General;'
                      '\\A\\1\\ \\(\\d\\a\\t\\a\\)')

  def test_format_round_trip (self):
    label = 'Sheet1.A1:A2 (pairs)'
    self.assertEqual (octave_core.label_of_format (
      octave_core.label_format (label)), label)

  def test_format_as_calc_keeps_it (self):
    # Read back from a cell in LibreOffice 25.2: the escape before the space
    # is gone
    code = ('General;-General;General;'
            '\\S\\h\\e\\e\\t\\2\\.\\A\\1\\:\\A\\3 \\(\\d\\a\\t\\a\\)')
    self.assertEqual (octave_core.label_of_format (code),
                      'Sheet2.A1:A3 (data)')

  def test_format_after_reload (self):
    # Read back from a cell of a reloaded document in LibreOffice 25.2
    code = '[>0]General;[<0]-General;General;"Sheet2.A1:A3 (data)"'
    self.assertEqual (octave_core.label_of_format (code),
                      'Sheet2.A1:A3 (data)')

  def test_format_other_condition (self):
    self.assertIsNone (octave_core.label_of_format (
      '[>5]General;[<0]-General;General;"J1:J4 (data)"'))

  def test_format_semicolon_in_label (self):
    label = 'Sheet;1.A1:A2 (data)'
    self.assertEqual (octave_core.label_of_format (
      octave_core.label_format (label)), label)

  def test_format_quoted (self):
    self.assertEqual (octave_core.label_of_format (
      'General;-General;General;"J1:J4 (data)"'), 'J1:J4 (data)')

  def test_format_bare_letter (self):
    self.assertIsNone (octave_core.label_of_format (
      'General;-General;General;\\J1 \\(\\d\\a\\t\\a\\)'))

  def test_other_format (self):
    self.assertIsNone (octave_core.label_of_format ('DD/MM/YYYY'))

  def test_general_alone (self):
    self.assertIsNone (octave_core.label_of_format ('General'))

  def test_literal_without_mode (self):
    self.assertIsNone (octave_core.label_of_format (
      octave_core.label_format ('A1:A2')))


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

  def test_not_available_value (self):
    built = self.expand ([[text ('Lambda'), {'kind': 'empty', 'na': True}]])
    self.assertEqual (built[2], octave_core.range_arg ([[EMPTY]]))

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


LIMITS = {'folders': ['/data/a', '/data/b'], 'packages': ['io', 'datatypes'],
          'memory': 4, 'tmp': 1, 'seconds': 10}


class LaunchCommand (unittest.TestCase):

  def test_plain (self):
    self.assertEqual (octave_core.launch_command ('/bin/octave-cli', LIMITS),
                      ['/bin/octave-cli', '-q', '--no-init-file', '--eval',
                       octave_core.LAUNCH])

  def test_through_systemd_run (self):
    command = octave_core.launch_command ('/bin/octave-cli', LIMITS, 'u1',
                                          {'HOME': '/home/x'})
    self.assertEqual (command[:command.index ('--')],
                      ['systemd-run', '--user', '--pipe', '--quiet',
                       '--collect', '--unit=u1',
                       '--setenv=DEVTOOLS_EVAL_SECONDS=10',
                       '--setenv=DEVTOOLS_SANDBOX_FOLDERS=/data/a:/data/b',
                       '--setenv=DEVTOOLS_SANDBOX_MEMORY=4',
                       '--setenv=DEVTOOLS_SANDBOX_PACKAGES=io,datatypes',
                       '--setenv=DEVTOOLS_SANDBOX_TMP=1',
                       '--setenv=HOME=/home/x'])

  def test_systemd_run_ends_with_plain_launch (self):
    command = octave_core.launch_command ('/bin/octave-cli', LIMITS, 'u1')
    self.assertEqual (command[command.index ('--') + 1:],
                      octave_core.launch_command ('/bin/octave-cli', LIMITS))


class SandboxConfirmed (unittest.TestCase):

  def test_reported (self):
    self.assertTrue (octave_core.sandbox_confirmed (
      {'_meta': {octave_core.SANDBOX_KEY: True}}))

  def test_absent (self):
    self.assertFalse (octave_core.sandbox_confirmed (
      {'protocolVersion': '2025-11-25'}))

  def test_no_result (self):
    self.assertFalse (octave_core.sandbox_confirmed (None))

  def test_only_true_counts (self):
    self.assertFalse (octave_core.sandbox_confirmed (
      {'_meta': {octave_core.SANDBOX_KEY: 'true'}}))


def bits (value):
  return '%016x' % struct.unpack ('<Q', struct.pack ('<d', value))[0]


def output (kind, rows, cols, cells):
  return {'kind': kind, 'class': '', 'rows': rows, 'cols': cols,
          'cells': cells}


class OutputRows (unittest.TestCase):

  def test_row_major (self):
    self.assertEqual (
      octave_core.output_rows (output ('number', 2, 2, [1, 2, 3, 4])),
      ((1.0, 2.0), (3.0, 4.0)))

  def test_inf (self):
    self.assertEqual (
      octave_core.output_rows (output ('number', 1, 2, ['Inf', '-Inf'])),
      ((float ('inf'), float ('-inf')),))

  def test_nan_shows_not_available (self):
    row = octave_core.output_rows (output ('number', 1, 1, [None]))[0]
    self.assertEqual (bits (row[0]), '7ff8000000007fff')

  def test_logical (self):
    self.assertEqual (
      octave_core.output_rows (output ('logical', 1, 2, [True, False])),
      ((1.0, 0.0),))

  def test_text_rows (self):
    self.assertEqual (
      octave_core.output_rows (output ('text', 2, 1, ['ab', 'cd'])),
      (('ab',), ('cd',)))

  def test_datetime_serial (self):
    self.assertEqual (
      octave_core.output_rows (output ('datetime', 1, 1, [45659])),
      ((45659.0,),))

  def test_cell_elements (self):
    cells = [{'kind': 'text', 'value': 'a'}, {'kind': 'number', 'value': 2},
             {'kind': 'empty'}]
    self.assertEqual (octave_core.output_rows (output ('cell', 1, 3, cells)),
                      (('a', 2.0, ''),))

  def test_empty_output (self):
    self.assertEqual (octave_core.output_rows (output ('number', 0, 0, [])),
                      (('',),))


SANDBOX = octave_core.sandbox_problem () is None
FUNCTIONS = os.path.join (os.path.dirname (os.path.abspath (__file__)),
                          'functions')


def settings (**changes):
  base = {'folders': [FUNCTIONS], 'packages': [], 'memory': 2, 'tmp': 2,
          'seconds': 10}
  base.update (changes)
  return base


def date_range ():
  return octave_core.range_arg ([[{'kind': 'date', 'value': 45658.0}]])


@unittest.skipUnless (SANDBOX, 'no sandbox on this machine')
class Server (unittest.TestCase):

  @classmethod
  def setUpClass (cls):
    cls.runner = octave_core.Server (settings ())

  @classmethod
  def tearDownClass (cls):
    cls.runner.stop ()

  def tearDown (self):
    octave_core.clear ()

  def call (self, name, *args):
    return octave_core.call (name, octave_core.build_args (args, no_key),
                             runner = self.runner)

  def test_empty_cell_is_nan (self):
    self.assertEqual (self.call ('mean', ((1.0, 2.0, 3.0), (4.0, '', 6.0)),
                                 2.0, 'omitnan'), ((2.0,), (5.0,)))

  def test_text_output (self):
    self.assertEqual (self.call ('upper', 'abc'), (('ABC',),))

  def test_cell_array_output (self):
    self.assertEqual (self.call ('strsplit', 'a,b', ','), (('a', 'b'),))

  def test_empty_elements (self):
    self.assertEqual (self.call ('cell', 1.0, 2.0), (('', ''),))

  def test_logical_output (self):
    self.assertEqual (self.call ('isnan', ((1.0, ''),)), ((0.0, 1.0),))

  def test_pairs_reach_function_as_options (self):
    rows = [[text ('Endpoints'), number (0.0)]]
    key = octave_core.range_key ('pairs', '$Sheet1.$A$1:$B$1', rows)
    args = octave_core.build_args ((((1.0, 2.0, 3.0, 4.0),), 3.0, key),
                                   keys ({key: (0, 0, rows)}))
    # Padding with 0 gives the ends (0+1+2)/3 and (3+4+0)/3; without the
    # option they would shrink to 1.5 and 3.5
    result = octave_core.call ('movmean', args, runner = self.runner)
    self.assertEqual ([round (v, 12) for v in result[0]],
                      [1.0, 2.0, 3.0, round (7.0 / 3, 12)])

  def test_folder_function (self):
    self.assertEqual (self.call ('octave_calc_twice', 2.0), ((4.0,),))

  def test_error_text_in_cell (self):
    self.assertIn ('not found', self.call ('octave_calc_no_such_function',
                                           1.0)[0][0])

  def test_system_refused (self):
    self.assertEqual (self.call ('system', 'true'),
                      (('octave-calc: system is not available in a '
                        'sandbox.',),))

  def test_dates_need_datatypes (self):
    self.assertEqual (
      octave_core.call ('class', [date_range ()], runner = self.runner),
      (('octave-calc: argument 1 holds dates or times, which need the '
        'datatypes package loaded in this sandbox.',),))

  def test_nan_result_shows_not_available (self):
    self.assertEqual (bits (self.call ('nan')[0][0]), '7ff8000000007fff')

  def test_not_available_input_is_nan (self):
    data = octave_core.range_arg ([[{'kind': 'empty', 'na': True},
                                    number (1.0)]])
    self.assertEqual (octave_core.call ('isnan', [data], runner = self.runner),
                      ((1.0, 0.0),))

  def test_infinite_numbers_reach_octave (self):
    rows = octave_core.numeric_texts ([[number (1.0), text ('Inf'),
                                        text ('-Inf')]])
    self.assertEqual (octave_core.call ('isinf', [octave_core.range_arg (rows)],
                                        runner = self.runner),
                      ((0.0, 1.0, 1.0),))

  def test_started_again_after_stop (self):
    self.runner.stop ()
    self.assertEqual (self.call ('mean', ((1.0, 3.0),)), ((2.0,),))


@unittest.skipUnless (SANDBOX, 'no sandbox on this machine')
class OwnServers (unittest.TestCase):

  def run_once (self, name, args, **changes):
    runner = octave_core.Server (settings (**changes))
    try:
      return octave_core.call (name, args, runner = runner)
    finally:
      runner.stop ()
      octave_core.clear ()

  def test_stopped_at_deadline (self):
    self.assertEqual (
      self.run_once ('octave_calc_wait', [{'type': 'number', 'value': 3.0}],
                     seconds = 1),
      (('octave-calc: the call to octave_calc_wait was stopped at the '
        'deadline of 1 seconds.',),))

  def test_dates_with_datatypes (self):
    self.assertEqual (
      self.run_once ('plus', [date_range (), {'type': 'number', 'value': 1.0}],
                     packages = ['datatypes']),
      ((45659.0,),))

  def test_missing_package_refused (self):
    result = self.run_once ('mean', [{'type': 'number', 'value': 1.0}],
                            packages = ['octave_calc_no_such_package'])
    self.assertIn ('octave_calc_no_such_package', result[0][0])


if (__name__ == '__main__'):
  unittest.main ()
