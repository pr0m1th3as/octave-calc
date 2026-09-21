#!/usr/bin/env python3
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

"""Build octave-calc.oxt, and optionally install it.

The only build step is compiling the interface declaration into a type
library.  That needs the LibreOffice SDK (Debian: libreoffice-dev), which is a
dependency of THIS machine and not of any user's: the .oxt ships the compiled
type library, LibreOffice registers it on install, and the result is
architecture-neutral, so there is no per-platform build.

Usage:
  python3 tools/build_oxt.py              build dist/octave-calc.oxt
  python3 tools/build_oxt.py --install    build, then install for this user
  python3 tools/build_oxt.py --remove     uninstall
"""

import io
import os
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname (os.path.dirname (os.path.abspath (__file__)))
BUILD = os.path.join (HERE, 'build')
DIST = os.path.join (HERE, 'dist')
IDENTIFIER = 'io.github.pr0m1th3as.octavecalc'

# description.xml holds the version, and the package is named after it, so
# that two builds of different versions can never arrive under one name.
DESCRIPTION = os.path.join (HERE, 'oxt', 'description.xml')


def version ():
  with io.open (DESCRIPTION, encoding = 'utf-8') as source:
    found = re.search (r'<version\s+value\s*=\s*"([^"]+)"', source.read ())
  if (not found):
    sys.exit ('no version in %s' % DESCRIPTION)
  return found.group (1)


VERSION = version ()
PACKAGE = os.path.join (DIST, 'octave-calc-%s.oxt' % VERSION)

SDK_BIN = '/usr/lib/libreoffice/sdk/bin'
OFFICE_TYPES = ('/usr/lib/libreoffice/program/types.rdb',
                '/usr/lib/libreoffice/program/types/offapi.rdb')

# Every analysis function, and the helpers they share, which must be listed
# here or the menu offers an analysis the sandbox cannot run.
ANALYSES = ('anova1', 'anova2', 'chi2gof', 'detectable', 'ff2n', 'fitdist',
            'friedman', 'fullfact', 'isoutlier', 'kruskalwallis',
            'normality', 'random', 'ranksum', 'sampsize', 'signrank', 'signtest',
            'testpower', 'ttest1', 'ttest2', 'ttestpaired', 'vartestn')

HELPERS = ('alpha', 'dof', 'dropped', 'factors', 'groups', 'matched', 'names',
           'pairs', 'sample', 'sampsizepwr', 'tail')

# Published path inside the package, against the source under the repository.
CONTENT = {'octave_calc.rdb': os.path.join (BUILD, 'octave_calc.rdb'),
           'addin.py': os.path.join (HERE, 'python', 'addin.py'),
           'octave_core.py': os.path.join (HERE, 'python', 'octave_core.py'),
           'octave_layout.py': os.path.join (HERE, 'python',
                                             'octave_layout.py'),
           'octave_literal.py': os.path.join (HERE, 'python',
                                              'octave_literal.py'),
           'octave_settings.py': os.path.join (HERE, 'python',
                                               'octave_settings.py'),
           'octave_stats.py': os.path.join (HERE, 'python', 'octave_stats.py'),
           'statistics_menu.py': os.path.join (HERE, 'python',
                                               'statistics_menu.py'),
           'OctaveCalc.xcs': os.path.join (HERE, 'oxt', 'OctaveCalc.xcs'),
           'CalcAddIns.xcu': os.path.join (HERE, 'oxt', 'CalcAddIns.xcu'),
           'Addons.xcu': os.path.join (HERE, 'oxt', 'Addons.xcu'),
           'icons/octave_16.png': os.path.join (HERE, 'oxt', 'icons',
                                                'octave_16.png'),
           'icons/octave_42.png': os.path.join (HERE, 'oxt', 'icons',
                                                'octave_42.png'),
           'COPYING': os.path.join (HERE, 'COPYING'),
           'ProtocolHandler.xcu': os.path.join (HERE, 'oxt',
                                                'ProtocolHandler.xcu'),
           'description.xml': os.path.join (HERE, 'oxt', 'description.xml'),
           'META-INF/manifest.xml': os.path.join (HERE, 'oxt', 'META-INF',
                                                  'manifest.xml')}

# Every extension description, one file per language, so that a
# translation is a file added beside the others and no edit here.
DESCRIPTIONS = os.path.join (HERE, 'oxt', 'descriptions')

CONTENT.update (dict (
  ('descriptions/%s' % name, os.path.join (DESCRIPTIONS, name))
  for name in sorted (os.listdir (DESCRIPTIONS))
  if name.endswith ('.txt')))

CONTENT.update (dict (
  ('octave/octave_calc_%s.m' % name,
   os.path.join (HERE, 'octave', 'octave_calc_%s.m' % name))
  for name in ANALYSES))

CONTENT.update (dict (
  ('octave/private/octave_calc_%s.m' % name,
   os.path.join (HERE, 'octave', 'private', 'octave_calc_%s.m' % name))
  for name in HELPERS))


def office_running ():
  return subprocess.call (['pgrep', '-x', 'soffice.bin'],
                          stdout = subprocess.DEVNULL) == 0


def compile_types ():
  tool = os.path.join (SDK_BIN, 'unoidl-write')
  if (not os.path.exists (tool)):
    sys.exit ('no %s.  Install the SDK: sudo apt install libreoffice-dev'
              % tool)
  os.makedirs (BUILD, exist_ok = True)
  output = os.path.join (BUILD, 'octave_calc.rdb')
  if (os.path.exists (output)):
    os.remove (output)
  source = os.path.join (HERE, 'idl', 'octave_calc.idl')
  subprocess.check_call ([tool] + list (OFFICE_TYPES) + [source, output])
  print ('types   %s (%d bytes)' % (output, os.path.getsize (output)))


def build ():
  compile_types ()
  os.makedirs (DIST, exist_ok = True)
  if (os.path.exists (PACKAGE)):
    os.remove (PACKAGE)
  with zipfile.ZipFile (PACKAGE, 'w', zipfile.ZIP_DEFLATED) as package:
    for name in sorted (CONTENT):
      source = CONTENT[name]
      if (not os.path.exists (source)):
        sys.exit ('missing %s' % source)
      package.write (source, name)
  print ('package %s (%d bytes, %d files)'
         % (PACKAGE, os.path.getsize (PACKAGE), len (CONTENT)))


def install ():
  if (office_running ()):
    sys.exit ('LibreOffice is running.  Close it first.')
  subprocess.check_call (['unopkg', 'add', '-f', PACKAGE])
  print ('installed %s' % IDENTIFIER)


def remove ():
  if (office_running ()):
    sys.exit ('LibreOffice is running.  Close it first.')
  subprocess.call (['unopkg', 'remove', IDENTIFIER])


if (__name__ == '__main__'):
  if ('--remove' in sys.argv):
    remove ()
  else:
    build ()
    if ('--install' in sys.argv):
      install ()
