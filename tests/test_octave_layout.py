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

"""Tests for octave_layout.  From the repository root:

  python3 -m unittest discover tests

These need neither LibreOffice nor Octave: the right side of the dialog is
laid out here in the dialog's own units, so every analysis can be laid out
and measured without one being opened.  What the tests hold is that each
block is given room for all of its words and that the last of them still
ends above the buttons.
"""

import ast
import os
import re
import sys
import unittest

ROOT = os.path.dirname (os.path.dirname (os.path.abspath (__file__)))
sys.path.insert (0, os.path.join (ROOT, 'python'))

import octave_layout
import octave_stats

# A line to spare under the last block of the tallest analysis, so that a
# word added to a hint is not a fault on the screen before it is one here.
SPARE = octave_layout.LINE


def every_plan ():
  """Every analysis laid out, both ways round for one whose results range
  may set the size of its draw."""
  for command in octave_stats.ANALYSES:
    for by_range in (False, True):
      yield command, octave_layout.plan (command, by_range)


def made ():
  """Every control the dialog makes, as a pattern each, read from the calls
  that make them.  A row of options is made eight times over, so a name
  built with a number in it stands for all of them."""
  tree = ast.parse (open (os.path.join (ROOT, 'python',
                                        'statistics_menu.py')).read ())
  patterns = []
  for node in ast.walk (tree):
    if (not isinstance (node, ast.Call)
        or not isinstance (node.func, ast.Name) or node.func.id != 'add'
        or len (node.args) < 2):
      continue
    name = node.args[1]
    if (isinstance (name, ast.Constant)):
      patterns.append (re.escape (name.value))
    elif (isinstance (name, ast.BinOp) and isinstance (name.op, ast.Mod)
          and isinstance (name.left, ast.Constant)):
      patterns.append (re.escape (name.left.value).replace ('%d', r'\d+'))
  # The layout buttons are made in a loop over the same tuple the layout
  # places them from, so the tuple is what the dialog makes them from
  patterns += [re.escape (name) for unused, name, label
               in octave_layout.RADIOS]
  return [re.compile ('%s$' % pattern) for pattern in patterns]


class Made (unittest.TestCase):
  """A control cannot be added once the dialog is open, so one the layout
  places and the dialog never made stops the dialog dead where it stands."""

  def test_every_control_placed_is_one_the_dialog_makes (self):
    patterns = made ()
    for command, laid in every_plan ():
      for name in laid:
        self.assertTrue (any (pattern.match (name) for pattern in patterns),
                         '%s %s' % (command, name))


class Lines (unittest.TestCase):
  """How many lines a hint takes across the column."""

  def test_nothing_takes_no_lines (self):
    self.assertEqual (octave_layout.lines (''), 0)

  def test_a_few_words_take_one (self):
    self.assertEqual (octave_layout.lines ('The chance of a false positive.'),
                      1)

  def test_a_sentence_past_the_width_takes_two (self):
    self.assertEqual (octave_layout.lines ('a b ' * 20), 2)

  def test_a_word_too_long_for_a_line_is_counted_as_more (self):
    """Counted generously, since a line too many leaves a gap where a line
    too few cuts the words off."""
    self.assertEqual (octave_layout.lines ('supercalifragilistic' * 4), 2)


class Fits (unittest.TestCase):
  """Every analysis is drawn whole, above the buttons."""

  def test_every_analysis_ends_above_the_buttons (self):
    for command, laid in every_plan ():
      self.assertLessEqual (octave_layout.bottom (laid),
                            octave_layout.BOTTOM - SPARE, command)

  def test_every_block_starts_below_the_top (self):
    for command, laid in every_plan ():
      for name, place in laid.items ():
        self.assertGreaterEqual (place['y'], octave_layout.TOP,
                                 '%s %s' % (command, name))

  def test_no_block_is_drawn_over_another (self):
    """Two blocks share a line only where they stand side by side, a label
    beside its field or one layout button beside the next."""
    for command, laid in every_plan ():
      places = sorted (laid.items (), key = lambda each: each[1]['y'])
      for (name, place), (below, under) in zip (places, places[1:]):
        if (place['y'] + place['height'] <= under['y']):
          continue
        self.assertFalse (
          place['x'] + place['width'] > under['x']
          and under['x'] + under['width'] > place['x'],
          '%s: %s over %s' % (command, name, below))

  def test_every_hint_is_given_room_for_all_of_its_words (self):
    for command, laid in every_plan ():
      for name, place in laid.items ():
        if ('label' in place):
          self.assertGreaterEqual (
            place['height'],
            octave_layout.words_height (place['label'])
            if place['width'] >= octave_layout.COLUMN else octave_layout.LINE,
            '%s %s' % (command, name))

  def test_an_analysis_draws_one_option_to_a_row (self):
    """A row holds whatever an option draws, so the rows the dialog holds
    ready are a count of options and not of lines."""
    for command in octave_stats.ANALYSES:
      self.assertLessEqual (len (octave_stats.slotted (command)),
                            octave_stats.OPTION_SLOTS, command)


class Hints (unittest.TestCase):
  """A hint is given the lines it needs, which is what the rank tests were
  refused when every row was one line tall."""

  def p_value (self, command):
    return octave_layout.plan (command)[
      'option%d_hint' % [option['name'] for option
                         in octave_stats.slotted (command)].index ('method')]

  def test_the_rank_tests_are_given_more_than_one_line (self):
    for command in ('Ranksum', 'SignRank', 'SignTest'):
      self.assertGreater (self.p_value (command)['height'],
                          octave_layout.LINE, command)

  def test_a_hint_says_what_it_is_given_room_for (self):
    place = self.p_value ('Ranksum')
    self.assertEqual (place['height'],
                      octave_layout.words_height (place['label']))

  def test_an_option_of_few_words_is_given_one_line (self):
    laid = octave_layout.plan ('Fitdist')
    self.assertEqual (laid['option0_hint']['height'], octave_layout.LINE)

  def test_a_hint_carries_the_longer_wording_as_its_tooltip (self):
    self.assertIn ('the group sizes choose',
                   self.p_value ('Ranksum')['help'])

  def test_every_option_of_a_group_comparison_teaches_on_hover (self):
    """The hint says it short and the tooltip says it at length.  Where
    the two are the same string, hovering adds nothing and the option is
    left with one sentence to do both jobs."""
    for command, analysis in octave_stats.ANALYSES.items ():
      if (analysis.get ('category') != 'Group comparisons'):
        continue
      for option in analysis['options']:
        where = '%s %s' % (command, option['name'])
        self.assertIn ('help', option, where)
        self.assertGreater (len (option['help']), len (option['hint']),
                            where)

  def test_every_group_comparison_says_how_much_room_it_needs (self):
    """The size of the results is read before the analysis is run, the
    whole point of it being to choose a corner with room below and to the
    right of it."""
    for command, analysis in octave_stats.ANALYSES.items ():
      if (analysis.get ('category') != 'Group comparisons'):
        continue
      words = octave_layout.plan (command)['output_hint']['label']
      self.assertIn ('8 columns', words, command)
      self.assertNotEqual (words, octave_layout.RESULTS_HINT, command)

  def test_an_analysis_without_a_size_keeps_the_plain_words (self):
    self.assertEqual (
      octave_layout.plan ('Fitdist')['output_hint']['label'],
      octave_layout.RESULTS_HINT)

  def test_no_hint_of_a_group_comparison_speaks_of_a_layout (self):
    """Nothing on screen is called a layout; the control the word meant
    is labelled Grouped by."""
    for kind in ('range', 'matched', 'factors', 'sample'):
      for words in (octave_layout.INPUT_HINT[kind],
                    octave_layout.INPUT_HELP[kind],
                    octave_layout.BY_HINT[kind]):
        self.assertNotIn ('layout', words, kind)


class Lists (unittest.TestCase):
  """A list is drawn the width its own entry gives it, beside the choices
  the entry lists, and a field's width where it gives none."""

  def listed (self, command, name):
    laid = octave_layout.plan (command)
    for slot, option in enumerate (octave_stats.slotted (command)):
      if (option['name'] == name):
        return (laid['option%d_%s' % (slot, 'list' if option.get ('rows')
                                      else 'box')],
                laid['option%d_label' % slot], option)
    raise KeyError (name)

  def test_a_list_is_drawn_the_width_its_entry_gives_it (self):
    for command in octave_stats.ANALYSES:
      for option in octave_stats.slotted (command):
        if (option['kind'] != 'choice'):
          continue
        place, unused, more = self.listed (command, option['name'])
        self.assertEqual (place['width'],
                          option.get ('width', octave_layout.OPTION_WIDTH),
                          '%s %s' % (command, option['name']))

  def test_a_width_leaves_its_label_a_row_to_stand_in (self):
    """A list stands at the right of the column and its label takes what is
    left, so a width that fills the column leaves no room to say what the
    list is for."""
    for command in octave_stats.ANALYSES:
      for option in octave_stats.slotted (command):
        if (option['kind'] != 'choice'):
          continue
        unused, label, more = self.listed (command, option['name'])
        self.assertGreaterEqual (label['width'], len (option['label']) * 4,
                                 '%s %s' % (command, option['name']))

  def test_a_list_stands_at_the_right_of_the_column (self):
    place, label, option = self.listed ('Isoutlier', 'method')
    self.assertEqual (place['width'], 130)
    self.assertEqual (place['x'] + place['width'],
                      octave_layout.LEFT + octave_layout.COLUMN)
    self.assertGreater (place['x'], label['x'] + label['width'])

  def test_a_list_whose_entry_says_nothing_is_a_field_wide (self):
    place, unused, more = self.listed ('KruskalWallis', 'ctype')
    self.assertEqual (place['width'], octave_layout.OPTION_WIDTH)


class Picking (unittest.TestCase):
  """Every button that picks a range with the mouse says the same thing."""

  def test_the_input_and_the_results_say_select (self):
    laid = octave_layout.plan ('KruskalWallis')
    self.assertEqual ([laid['input_pick']['label'],
                       laid['output_pick']['label']],
                      [octave_layout.PICK, octave_layout.PICK])

  def test_every_custom_slot_says_the_same (self):
    laid = octave_layout.plan ('Custom')
    for name in laid:
      if (name.endswith ('_pick')):
        self.assertEqual (laid[name]['label'], octave_layout.PICK, name)

  def test_a_custom_slot_has_a_button_each (self):
    laid = octave_layout.plan ('Custom')
    self.assertEqual (len ([name for name in laid
                            if name.endswith ('_pick')]),
                      octave_stats.CUSTOM_SLOTS
                      + octave_stats.CUSTOM_OUTPUTS)

  def test_a_button_is_the_same_width_wherever_it_stands (self):
    laid = dict (octave_layout.plan ('KruskalWallis'))
    laid.update (octave_layout.plan ('Custom'))
    for name, place in laid.items ():
      if (name.endswith ('_pick')):
        self.assertEqual ((place['x'], place['width']),
                          (octave_layout.PICK_LEFT, octave_layout.PICK_WIDTH),
                          name)


class Drawn (unittest.TestCase):
  """An analysis is drawn what it takes and nothing else."""

  def test_a_layout_an_analysis_does_not_take_is_not_drawn (self):
    laid = octave_layout.plan ('SignRank')
    self.assertEqual ([name for unused, name, label in octave_layout.RADIOS
                       if name in laid],
                      ['columns', 'rows'])

  def test_the_layouts_are_drawn_two_to_a_row (self):
    laid = octave_layout.plan ('KruskalWallis')
    self.assertEqual (laid['columns']['y'], laid['rows']['y'])
    self.assertGreater (laid['labels_data']['y'], laid['columns']['y'])

  def test_an_analysis_that_reads_no_cells_is_drawn_no_range (self):
    laid = octave_layout.plan ('FullFactorial')
    self.assertNotIn ('input', laid)
    self.assertNotIn ('by_label', laid)
    self.assertIn ('output', laid)

  def test_a_generator_is_drawn_its_size_and_its_seed (self):
    laid = octave_layout.plan ('RandomNormal')
    self.assertIn ('rows_draw', laid)
    self.assertIn ('seed', laid)
    self.assertNotIn ('size_text', laid)

  def test_a_results_range_of_more_than_one_cell_takes_their_place (self):
    laid = octave_layout.plan ('RandomNormal', True)
    self.assertIn ('size_text', laid)
    self.assertNotIn ('rows_draw', laid)

  def test_the_chooser_is_called_what_the_analysis_reads (self):
    self.assertEqual (octave_layout.plan ('SignRank')['by_label']['label'],
                      'Measurements in:')
    self.assertEqual (octave_layout.plan ('Anova1')['by_label']['label'],
                      'Grouped by:')

  def test_the_custom_analysis_draws_its_own_side (self):
    laid = octave_layout.plan ('Custom')
    self.assertIn ('in_head', laid)
    self.assertNotIn ('output_label', laid)
    self.assertNotIn ('option0_label', laid)

  def test_an_analysis_of_ours_draws_no_custom_slot (self):
    laid = octave_layout.plan ('Ttest1')
    self.assertNotIn ('in0_text', laid)
    self.assertIn ('option0_label', laid)

  def test_nothing_is_drawn_where_a_category_holds_no_analysis (self):
    self.assertEqual (octave_layout.plan (None), {})


if (__name__ == '__main__'):
  unittest.main ()
