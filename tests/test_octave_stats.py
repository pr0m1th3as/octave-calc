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

import ast
import importlib.util
import math
import io
import os
import re
import sys
import unittest
import xml.dom.minidom

ROOT = os.path.dirname (os.path.dirname (os.path.abspath (__file__)))
sys.path.insert (0, os.path.join (ROOT, 'python'))

import octave_core
import octave_settings
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
                      'C7 holds the text "x".  The input range may hold '
                      'group names in its first row, then numbers and empty '
                      'cells only.')

  def test_text_refused_by_cell_beside_header (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.group_args ((('A', 1.0), ('B', 'x')), 'rows', 2, 4)
    self.assertEqual (str (raised.exception),
                      'D6 holds the text "x".  The input range may hold '
                      'group names in its first column, then numbers and '
                      'empty cells only.')

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
                      'C6 holds the text "x".  The values may be numbers '
                      'or empty cells, and the group labels text or '
                      'numbers.')

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
                      'A2 holds the text "oops".  The values may be '
                      'numbers or empty cells, and the factor labels text or '
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
    """The Custom analysis apart, which runs the user's own function and
    has no file of ours to package."""
    for command, analysis in octave_stats.ANALYSES.items ():
      if (analysis.get ('custom')):
        continue
      self.assertIn ('octave/%s.m' % analysis['function'],
                     self.build.CONTENT, command)

  def test_the_custom_analysis_names_no_function_of_ours (self):
    self.assertEqual (octave_stats.ANALYSES['Custom']['function'], '')

  def test_every_octave_file_is_packaged (self):
    for folder, published in (('octave', 'octave/%s'),
                              (os.path.join ('octave', 'private'),
                               'octave/private/%s')):
      for name in os.listdir (os.path.join (ROOT, folder)):
        if (name.endswith ('.m')):
          self.assertIn (published % name, self.build.CONTENT, name)

  def test_every_python_module_is_packaged (self):
    """A module left out of the package is imported by nothing and the
    component fails to load, which the dialog cannot report."""
    for name in os.listdir (os.path.join (ROOT, 'python')):
      if (name.endswith ('.py')):
        self.assertIn (name, self.build.CONTENT, name)

  def test_every_packaged_source_exists (self):
    for published, source in self.build.CONTENT.items ():
      if ('build' not in source):
        self.assertTrue (os.path.exists (source), published)


class Described (unittest.TestCase):
  """description.xml is the one place the version is written, and every file
  it names must be in the package or the Extension Manager shows nothing
  where the icon and the description belong."""

  def setUp (self):
    spec = importlib.util.spec_from_file_location (
      'build_oxt', os.path.join (ROOT, 'tools', 'build_oxt.py'))
    self.build = importlib.util.module_from_spec (spec)
    spec.loader.exec_module (self.build)
    self.described = xml.dom.minidom.parse (
      os.path.join (ROOT, 'oxt', 'description.xml'))
    self.feed = xml.dom.minidom.parse (
      os.path.join (ROOT, 'docs', 'octave-calc.update.xml'))

  def valued (self, document, tag):
    return document.getElementsByTagName (tag)[0].getAttribute ('value')

  def hrefs (self, document):
    return [node.getAttribute ('xlink:href')
            for node in document.getElementsByTagName ('*')
            if node.getAttribute ('xlink:href')]

  def test_the_version_is_written_once (self):
    """octave_core reports it to the server and the build names the package
    after it, both from description.xml."""
    said = self.valued (self.described, 'version')
    self.assertEqual (octave_core.VERSION, said)
    self.assertEqual (self.build.VERSION, said)
    self.assertTrue (self.build.PACKAGE.endswith ('octave-calc-%s.oxt' % said),
                     self.build.PACKAGE)

  def test_every_file_it_names_is_packaged (self):
    for href in self.hrefs (self.described):
      if (href.startswith ('http')):
        continue
      self.assertIn (href, self.build.CONTENT, href)

  def test_the_minimum_is_declared_where_libreoffice_reads_it (self):
    """LibreOffice-minimal-version lives in LibreOffice's own namespace.
    Written in the OpenOffice description namespace it is an unknown
    dependency, and an unknown dependency is unsatisfiable, so the
    extension refuses to install on every LibreOffice there is.
    OpenOffice.org-minimal-version is read instead against the OpenOffice
    version LibreOffice reports for compatibility, which is 4.1."""
    found = self.described.getElementsByTagNameNS (
      'http://libreoffice.org/extensions/description/2011',
      'LibreOffice-minimal-version')
    self.assertEqual (len (found), 1)
    self.assertTrue (found[0].getAttribute ('value'))
    self.assertEqual (
      self.described.getElementsByTagName ('OpenOffice.org-minimal-version'),
      [])

  def test_the_licence_is_packaged (self):
    """A GPL extension that ships without its licence is not one."""
    self.assertIn ('COPYING', self.build.CONTENT)

  def test_every_language_it_offers_has_a_file (self):
    """A src naming a language whose file is not packaged leaves the
    Extension Manager blank for every user in that language."""
    for node in self.described.getElementsByTagName ('src'):
      href = node.getAttribute ('xlink:href')
      if (href.startswith ('http')):
        continue
      self.assertTrue (node.getAttribute ('lang'), href)
      self.assertIn (href, self.build.CONTENT, href)

  def test_every_packaged_description_is_offered (self):
    """The folder is packaged wholesale, so a file added without a src
    beside it ships and is never shown."""
    offered = set (node.getAttribute ('xlink:href')
                   for node in self.described.getElementsByTagName ('src'))
    for name in self.build.CONTENT:
      if (name.startswith ('descriptions/')):
        self.assertIn (name, offered, name)

  def test_the_update_feed_matches_the_extension (self):
    """The feed is edited by hand at each release, and a version left
    behind offers nobody anything."""
    self.assertEqual (self.valued (self.feed, 'identifier'),
                      self.valued (self.described, 'identifier'))
    self.assertEqual (self.valued (self.feed, 'version'),
                      self.valued (self.described, 'version'))

  def test_the_feed_points_at_the_package_this_build_makes (self):
    named = os.path.basename (self.build.PACKAGE)
    downloads = [href for href in self.hrefs (self.feed)
                 if href.endswith ('.oxt')]
    self.assertEqual (len (downloads), 1)
    self.assertTrue (downloads[0].endswith ('/' + named), downloads[0])


class Localizable (unittest.TestCase):
  """LibreOffice chooses a value by the UI language and falls back to
  en-US, so every translatable value carries that tag and a translation is
  a sibling beside it.  Nothing here is read by our own code."""

  FILES = ('CalcAddIns.xcu', 'Addons.xcu')

  # The names a formula is written with, which stay English whatever the UI
  # language: the first argument of OCTAVE is an Octave function's name.
  UNTRANSLATED = ('DisplayName', 'CompatibilityName')

  def valued (self, name):
    with io.open (os.path.join (ROOT, 'oxt', name),
                  encoding = 'utf-8') as held:
      return re.findall (r'<prop oor:name="(\w+)"[^>]*>\s*'
                         r'<value xml:lang="([^"]+)"', held.read ())

  def test_one_language_tag_throughout (self):
    for name in self.FILES:
      found = self.valued (name)
      self.assertTrue (found, name)
      for prop, tag in found:
        self.assertEqual (tag, 'en-US', '%s %s' % (name, prop))

  def test_the_function_names_are_not_offered_for_translation (self):
    """Their values are one word each, the name itself; a Description is
    what a translator is given."""
    for prop, unused in self.valued ('CalcAddIns.xcu'):
      self.assertIn (prop, self.UNTRANSLATED + ('Description',), prop)


class Published (unittest.TestCase):
  """What Pages serves is written from RELEASE_NOTES and description.xml by
  tools/publish_release.py.  Left behind, the Extension Manager offers the
  notes of the release before this one, or an asset that is not there.

  RELEASE_NOTES is the maintainer's working copy and is not in the
  repository, so these run where it is present and are skipped where it is
  not: a clone can build, test and install without it."""

  NOTES = os.path.join (ROOT, 'RELEASE_NOTES')

  def setUp (self):
    if (not os.path.exists (self.NOTES)):
      self.skipTest ('no RELEASE_NOTES here; only publishing needs it')
    spec = importlib.util.spec_from_file_location (
      'publish_release', os.path.join (ROOT, 'tools', 'publish_release.py'))
    self.publish = importlib.util.module_from_spec (spec)
    spec.loader.exec_module (self.publish)

  def test_what_pages_serves_is_current (self):
    for path, text in self.publish.wanted ().items ():
      at = os.path.relpath (path, ROOT)
      self.assertTrue (os.path.exists (path), at)
      self.assertEqual (self.publish.read (path), text, at)

  def test_the_notes_open_on_the_version_being_released (self):
    first = self.publish.read (self.NOTES).split ('\n', 1)[0]
    self.assertIn (self.publish.version (), first)


class Settings (unittest.TestCase):
  """A deadline is read by a role, and the key it maps to must be declared
  in the schema: a half-finished rename asks the configuration for a name
  that is not there, which only a run in LibreOffice would show."""

  def setUp (self):
    self.schema = xml.dom.minidom.parse (
      os.path.join (ROOT, 'oxt', 'OctaveCalc.xcs'))

  def declared (self):
    return set (node.getAttribute ('oor:name')
                for node in self.schema.getElementsByTagName ('prop'))

  def test_every_deadline_is_declared (self):
    for role, key in octave_settings.SECONDS.items ():
      self.assertIn (key, self.declared (), role)

  def test_every_role_asked_for_has_a_deadline (self):
    asked = set ()
    for name in ('statistics_menu.py', 'addin.py'):
      with io.open (os.path.join (ROOT, 'python', name),
                    encoding = 'utf-8') as held:
        asked.update (re.findall (
          r"octave_settings\.read \([^,]+, '(\w+)'\)", held.read ()))
    self.assertTrue (asked)
    for role in asked:
      self.assertIn (role, octave_settings.SECONDS, role)


class CustomArgs (unittest.TestCase):
  """The Custom analysis builds its own arguments: what is typed is read as
  a literal, and what is not a literal is a range the caller resolves."""

  def resolve (self, text, what, refusal):
    if (text.strip () == 'A1:B2'):
      return {'type': 'range', 'rows': 1, 'cols': 1, 'cells': []}
    raise ValueError ('the %s is not a range in this document.' % what)

  def args (self, slots, pairs = ''):
    return octave_stats.custom_args (slots, pairs, self.resolve)

  def test_a_literal_is_read_here (self):
    self.assertEqual (self.args (['3', '', '', '']),
                      [{'type': 'number', 'value': 3.0}])

  def test_what_is_not_a_literal_is_resolved (self):
    self.assertEqual ([arg['type'] for arg in self.args (['A1:B2', '', '',
                                                          ''])],
                      ['range'])

  def test_filled_slots_keep_their_order (self):
    self.assertEqual ([arg['type'] for arg in self.args (['A1:B2', '3', '',
                                                          ''])],
                      ['range', 'number'])

  def test_pairs_follow_the_last_slot (self):
    self.assertEqual ([arg['type'] for arg in
                       self.args (['A1:B2', '', '', ''], "{'N', 2}")],
                      ['range', 'string', 'number'])

  def test_pairs_alone (self):
    self.assertEqual (len (self.args (['', '', '', ''], "{'N', 2}")), 2)

  def test_nothing_at_all_passes_nothing (self):
    self.assertEqual (self.args (['', '', '', '']), [])

  def test_filled_counts_from_the_first (self):
    self.assertEqual (octave_stats.filled (['a', 'b', '', ''], 'input'), 2)

  def test_filled_counts_none (self):
    self.assertEqual (octave_stats.filled (['', '', ''], 'output'), 0)

  def test_filled_names_the_gap_in_its_own_words (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.filled (['D1', '', 'F1'], 'output')
    self.assertEqual (str (raised.exception),
                      'output 2 is empty and output 3 is not; the outputs '
                      'are filled from the first.')

  def test_a_gap_is_refused (self):
    with self.assertRaises (ValueError) as raised:
      self.args (['', '3', '', ''])
    self.assertEqual (str (raised.exception),
                      'input 1 is empty and input 2 is not; the inputs are '
                      'filled from the first.')

  def test_a_later_gap_is_refused (self):
    with self.assertRaises (ValueError):
      self.args (['1', '2', '', '4'])

  def test_neither_a_literal_nor_a_range_is_refused (self):
    with self.assertRaises (ValueError) as raised:
      self.args (['pi', '', '', ''])
    self.assertEqual (str (raised.exception),
                      'the input 1 is not a range in this document.')


class DialogControls (unittest.TestCase):
  """Every control of the dialog is named, and UNO refuses a name given
  twice.  It refuses it while the dialog is still being built, so the whole
  dialog is lost, and the menu entry then does nothing at all: there is no
  half-drawn dialog to notice and the reason only reaches the error output.
  The names are read out of the source, since the dialog itself cannot be
  built without LibreOffice.

  It is worth a test of its own because the layout buttons are named after
  the layouts, which are ordinary words like rows and columns that a field
  added later would want too."""

  def names (self):
    with open (os.path.join (ROOT, 'python', 'statistics_menu.py')) as source:
      tree = ast.parse (source.read ())
    found = []
    boxes = 1
    for node in ast.walk (tree):
      if (isinstance (node, ast.Assign)
          and any (getattr (target, 'id', None) == 'CHECK_BOXES'
                   for target in node.targets)):
        boxes = node.value.value
    for node in ast.walk (tree):
      # The layout buttons, named from the RADIOS table
      if (isinstance (node, ast.Assign)
          and any (getattr (target, 'id', None) == 'RADIOS'
                   for target in node.targets)):
        found.extend (row.elts[0].value for row in node.value.elts)
      # Every other control, named in its own add () call
      if (not (isinstance (node, ast.Call)
               and getattr (node.func, 'id', None) == 'add'
               and len (node.args) > 1)):
        continue
      name = node.args[1]
      if (isinstance (name, ast.Constant)):
        found.append (name.value)
      elif (isinstance (name, ast.BinOp)
            and isinstance (name.left, ast.Constant)):
        # An option row, one per slot, and a box of a row one per box
        pattern = name.left.value
        for slot in range (octave_stats.OPTION_SLOTS):
          if (pattern.count ('%d') > 1):
            found.extend (pattern % (slot, box) for box in range (boxes))
          else:
            found.append (pattern % slot)
    return found

  def test_the_dialog_is_read (self):
    self.assertIn ('category', self.names ())

  def test_every_control_is_named_once (self):
    names = self.names ()
    self.assertEqual (sorted (name for name in set (names)
                              if names.count (name) > 1), [])


class Registry (unittest.TestCase):

  OPTIONAL = {'sized', 'seeded', 'listed', 'heading', 'custom', 'results'}

  def test_every_analysis_is_complete (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      self.assertEqual (sorted (set (analysis) - self.OPTIONAL),
                        ['category', 'detail', 'function', 'input', 'layouts',
                         'options', 'title'], command)
      declared = [option['name'] for option in analysis['options']]
      for name in analysis.get ('sized', ()):
        self.assertIn (name, declared, command)
      if ('seeded' in analysis):
        self.assertIn (analysis['seeded'], declared, command)
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
                       {'type': 'string', 'value': 'sample'},
                       {'type': 'string', 'value': ''},
                       {'type': 'number', 'value': 0.05}])

  def test_option_args_of_isoutlier (self):
    self.assertEqual (octave_stats.option_args ('Isoutlier', {}),
                      [{'type': 'string', 'value': 'median'},
                       {'type': 'number', 'value': 0.0}])

  def test_every_refusal_names_what_the_analysis_reads (self):
    """A sample has one name where groups have several, which a shared
    frame with a noun dropped into it could not say."""
    self.assertIn ('the sample name',
                   octave_stats.allowed ('columns', 'sample'))
    self.assertIn ('group names', octave_stats.allowed ('columns', 'range'))
    self.assertIn ('measurement names',
                   octave_stats.allowed ('rows', 'matched'))

  def test_every_kind_and_layout_has_a_refusal (self):
    for kind in octave_stats.NOUN:
      for by in ('columns', 'rows', 'labels-data', 'data-labels'):
        self.assertTrue (octave_stats.allowed (by, kind).endswith ('.'),
                         '%s %s' % (kind, by))

  def test_options_fit_the_dialog (self):
    """One option is drawn in one row, whatever it draws, so the cap is on
    the options an analysis declares.  The size and the seed have fields of
    their own and a fixed value is never drawn."""
    for command in octave_stats.ANALYSES:
      self.assertLessEqual (len (octave_stats.slotted (command)),
                            octave_stats.OPTION_SLOTS, command)

  def test_a_stack_of_boxes_fits_the_row_it_is_drawn_in (self):
    """A row holds a fixed number of boxes, since a control cannot be added
    once the dialog is open."""
    for command in octave_stats.ANALYSES:
      for option in octave_stats.slotted (command):
        if (option['kind'] == 'checks'):
          self.assertLessEqual (len (option['choices']),
                                octave_stats.CHECK_BOXES, option['name'])

  def test_ticked_boxes_reach_octave_in_declared_order (self):
    option = octave_stats.option_named ('Fitdist', 'parts')
    self.assertEqual (octave_stats.ticked (option, 'cdf pdf'),
                      ('pdf', 'cdf'))

  def test_no_box_ticked_reaches_octave_as_nothing (self):
    self.assertEqual (
      octave_stats.option_args ('Fitdist', {'parts': ''})[2],
      {'type': 'string', 'value': ''})

  def test_one_box_ticked_reaches_octave_alone (self):
    self.assertEqual (
      octave_stats.option_args ('Fitdist', {'parts': 'cdf'})[2],
      {'type': 'string', 'value': 'cdf'})

  def test_slotted_leaves_out_what_is_drawn_elsewhere (self):
    self.assertEqual ([option['name']
                       for option in octave_stats.slotted ('RandomNormal')],
                      ['mu', 'sigma'])

  def test_slotted_holds_every_option_by_default (self):
    self.assertEqual ([option['name']
                       for option in octave_stats.slotted ('Ttest1')],
                      ['nullmean', 'tail', 'alpha'])

  def test_the_generator_list_is_called_what_it_holds (self):
    self.assertEqual (octave_stats.list_label ('Random numbers'),
                      'Available generators:')

  def test_every_other_list_is_called_the_analysis (self):
    self.assertEqual (octave_stats.list_label ('Group comparisons'),
                      'Analysis:')

  def test_generator_rows_are_called_the_parameters (self):
    self.assertEqual (octave_stats.heading ('RandomNormal'),
                      'Distribution parameters:')

  def test_other_rows_are_called_the_options (self):
    self.assertEqual (octave_stats.heading ('Ttest1'), 'Options:')

  def test_a_generator_is_listed_by_its_name_alone (self):
    self.assertEqual (octave_stats.listed ('RandomNormal'), 'Normal')
    self.assertEqual (octave_stats.ANALYSES['RandomNormal']['title'],
                      'Normal random numbers')

  def test_an_analysis_is_listed_by_its_title (self):
    self.assertEqual (octave_stats.listed ('Ttest1'), 'One-sample t-test')

  def test_analyses_of_experimental_design (self):
    self.assertEqual (octave_stats.analyses_of ('Experimental design'),
                      ('FullFactorial', 'TwoLevelFactorial', 'SampleSize',
                       'TestPower', 'Detectable'))

  def test_power_options_reach_octave_in_order (self):
    args = octave_stats.option_args ('SampleSize', {})
    self.assertEqual ([arg['value'] for arg in args],
                      ['t', 5.0, 2.0, 6.0, 0.9, 0.05])

  def test_a_generator_for_every_distribution (self):
    self.assertEqual (octave_stats.analyses_of ('Random numbers'),
                      tuple ('Random%s' % name
                             for name, unused, more in
                             octave_stats.GENERATORS))

  def test_a_generator_passes_its_distribution_first (self):
    self.assertEqual (octave_stats.option_args ('RandomPoisson', {}),
                      [{'type': 'string', 'value': 'Poisson'},
                       {'type': 'number', 'value': 10.0},
                       {'type': 'number', 'value': 1.0},
                       {'type': 'string', 'value': ''},
                       {'type': 'number', 'value': 1.0}])

  def test_a_parameter_says_what_it_is_beside_its_name (self):
    self.assertEqual ([(option['label'], option['note'])
                       for option in octave_stats.slotted ('RandomNormal')],
                      [('mu:', 'mean'), ('sigma:', 'standard deviation')])

  def test_a_note_fits_beside_the_field (self):
    """The note is drawn in a control of a fixed width, so one too long is
    cut off rather than wrapped."""
    for command in octave_stats.ANALYSES:
      for option in octave_stats.slotted (command):
        note = option.get ('note')
        if (note is not None):
          self.assertLessEqual (len (note), octave_stats.NOTE_LIMIT,
                                '%s %s' % (command, option['name']))
          self.assertEqual (note, note.lower (), note)

  def test_a_generator_takes_its_parameters_in_order (self):
    self.assertEqual ([option['label']
                       for option in octave_stats.slotted ('RandomStable')],
                      ['alpha:', 'beta:', 'gam:', 'delta:'])

  def test_a_parameter_may_reach_a_bound_it_is_allowed (self):
    """Binomial's p is bounded in [0, 1], which the open check the other
    options use would refuse at either end."""
    self.assertEqual (octave_stats.option_args ('RandomBinomial',
                                                {'p': '1'})[4]['value'], 1.0)

  def test_a_parameter_past_a_bound_is_refused (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.option_args ('RandomBinomial', {'p': '1.5'})
    self.assertEqual (str (raised.exception),
                      'the probability of success must be a number '
                      'from 0 to 1.')

  def test_a_whole_parameter_is_refused_a_fraction (self):
    with self.assertRaises (ValueError) as raised:
      octave_stats.option_args ('RandomBinomial', {'N': '2.5'})
    self.assertEqual (str (raised.exception),
                      'the number of trials must be a whole number '
                      'greater than 0.')

  def test_what_the_bounds_take_is_one_whole_sentence (self):
    """The refusal and the tooltip's last sentence, both written out,
    neither assembled from a frame and a fragment."""
    for held, refusal, takes in (
        (octave_stats.ANY, octave_stats.TAKES_ANY, 'Takes a number.'),
        (octave_stats.POSITIVE, octave_stats.TAKES_POSITIVE,
         'Takes a number greater than 0.'),
        (octave_stats.FROM_HALF, octave_stats.TAKES_FROM_HALF,
         'Takes a number of 0.5 or more.'),
        (octave_stats.TO_TWO, octave_stats.TAKES_TO_TWO,
         'Takes a number greater than 0 and no more than 2.'),
        (octave_stats.SKEW, octave_stats.TAKES_SKEW,
         'Takes a number from -1 to 1.')):
      self.assertEqual (octave_stats.bounded (held), (refusal, takes))

  def test_every_shape_the_generators_use_has_words (self):
    """A parameter whose bounds are not in BOUNDED reaches the user with
    no words at all, which is a KeyError at import."""
    for command, analysis in octave_stats.ANALYSES.items ():
      for option in analysis['options']:
        if ('note' not in option):
          continue
        self.assertIn (octave_stats.shape (option), octave_stats.BOUNDED,
                       '%s %s' % (command, option['name']))

  def test_every_category_holds_an_analysis (self):
    """A category joins the dialog with the analyses that fill it, so a
    listed one is never empty."""
    for category in octave_stats.CATEGORIES:
      self.assertNotEqual (octave_stats.analyses_of (category), (), category)

  def test_every_analysis_is_in_a_listed_category (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      self.assertIn (analysis['category'], octave_stats.CATEGORIES, command)

  def test_first_analysis (self):
    self.assertEqual (octave_stats.first_analysis (), 'KruskalWallis')

  def test_every_option_is_complete (self):
    for command, analysis in octave_stats.ANALYSES.items ():
      for option in analysis['options']:
        self.assertTrue ({'name', 'kind', 'label', 'hint', 'default'}
                         <= set (option), option)
        self.assertIn (option['kind'],
                       ('choice', 'number', 'numbers', 'radios', 'checks',
                        'text', 'fixed'),
                       option['name'])
        if (option['kind'] == 'radios'):
          self.assertEqual (len (option['choices']), 2, option['name'])
        if (option['kind'] in ('number', 'numbers')):
          self.assertTrue ({'refusal', 'minimum', 'maximum'} <= set (option),
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
            'refusal': octave_stats.TAKES_OPEN_UNIT,
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
            'refusal': octave_stats.TAKES_LEVELS,
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
      {'folders': [os.path.join (ROOT, 'octave'),
                   os.path.join (ROOT, 'tests', 'functions')],
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
      'B2 holds the text "oops".  The input range may hold measurement '
      'names in its first row, then numbers and empty cells only.')

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
    """A generator returns the drawn numbers and nothing else, so the block
    written is exactly the size asked for and every cell is a number."""
    table = self.run_analysis ((), 'columns', 'RandomNormal',
                               {'mu': '5', 'sigma': '2', 'nrows': '3',
                                'ncols': '4', 'seed': '7'})
    self.assertEqual ((len (table), len (table[0])), (3, 4))
    for line in table:
      for value in line:
        self.assertIsInstance (value, float)

  def test_a_seed_that_was_not_given_still_draws (self):
    table = self.run_analysis ((), 'columns', 'RandomNormal',
                               {'nrows': '2', 'ncols': '2'})
    self.assertEqual ((len (table), len (table[0])), (2, 2))

  def test_the_drawn_distributions_are_the_ones_makedist_takes (self):
    """Every distribution the dialog offers must be one makedist builds
    from a number per parameter; the three it cannot are left out."""
    listed = self.runner.call ('makedist', [])
    named = set (line[0] for line in octave_core.output_rows (listed[0]))
    offered = set (name for name, unused, more in octave_stats.GENERATORS)
    self.assertEqual (named - offered,
                      {'Kernel', 'Multinomial', 'PiecewiseLinear'})

  def test_every_generator_names_the_parameters_makedist_names (self):
    """The dialog labels each field with a parameter name and passes the
    numbers in that order, so a name or an order that drifts upstream puts
    the values into the wrong parameters in silence."""
    for name, unused, parameters in octave_stats.GENERATORS:
      declared = self.runner.call (
        'octave_calc_parameters', [{'type': 'string', 'value': name}])
      self.assertEqual (
        [line[0] for line in octave_core.output_rows (declared[0])],
        [parameter for parameter, d, b, v in parameters], name)

  def test_every_generator_is_listed_as_the_distribution_names_itself (self):
    for name, unused, more in octave_stats.GENERATORS:
      declared = self.runner.call (
        'octave_calc_parameters', [{'type': 'string', 'value': name}],
        nargout = 2)
      self.assertEqual (octave_stats.readable (name),
                        octave_core.output_rows (declared[1])[0][0], name)

  def test_every_generator_draws (self):
    """A parameter's default must be one its own distribution accepts, or
    the generator refuses before the user has touched anything."""
    for name, unused, more in octave_stats.GENERATORS:
      table = self.run_analysis ((), 'columns', 'Random%s' % name,
                                 {'nrows': '2', 'ncols': '2', 'seed': '1'})
      self.assertEqual ((len (table), len (table[0])), (2, 2), name)

  def test_refusal_names_no_function (self):
    with self.assertRaises (RuntimeError) as raised:
      self.run_analysis (((1.0,), (2.0,)), 'columns')
    self.assertEqual (
      octave_stats.reason (str (raised.exception),
                           'octave_calc_kruskalwallis'),
      'the input range holds fewer than two groups.')


if (__name__ == '__main__'):
  unittest.main ()
