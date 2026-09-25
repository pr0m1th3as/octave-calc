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

"""Install a built package into a new LibreOffice profile and check that
LibreOffice took all of it: the identifier and version the package declares,
and every part its manifest lists, each registered.  The profile is made for
the check and removed after it, so the user's own is never touched.

Usage:
  python3 tools/check_install.py UNOPKG PACKAGE

UNOPKG is the unopkg program of the LibreOffice to install into: unopkg.com
on Windows, where unopkg.exe writes nothing to the console.
"""

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile


def declared (package):
  """The identifier, the version and the manifest's parts of PACKAGE."""
  with zipfile.ZipFile (package) as source:
    description = source.read ('description.xml').decode ('utf-8')
    manifest = source.read ('META-INF/manifest.xml').decode ('utf-8')
  identifier = re.search (r'<identifier\s+value\s*=\s*"([^"]+)"', description)
  version = re.search (r'<version\s+value\s*=\s*"([^"]+)"', description)
  if (not identifier or not version):
    sys.exit ('%s declares no identifier or no version.' % package)
  parts = re.findall (r'manifest:full-path\s*=\s*"([^"]+)"', manifest)
  return identifier.group (1), version.group (1), parts


def unopkg (program, profile, *args):
  """Run PROGRAM on PROFILE with ARGS, and return its exit status and what
  it wrote."""
  done = subprocess.run ([program] + list (args)
                         + ['-env:UserInstallation=' + profile],
                         stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
  return done.returncode, done.stdout.decode ('utf-8', 'replace')


def problems (listing, identifier, version, parts):
  """What LISTING, unopkg's list of IDENTIFIER, shows wrong, one line each."""
  found = []
  top = re.search (r'Identifier:\s*(\S+)\s+Version:\s*(\S+)\s+URL:\s*\S+\s+'
                   r'is registered:\s*(\S+)', listing)
  if (not top):
    return ['the package is not listed.']
  if (top.group (1) != identifier):
    found.append ('listed as %s, not %s.' % (top.group (1), identifier))
  if (top.group (2) != version):
    found.append ('listed at version %s, not %s.' % (top.group (2), version))
  if (top.group (3) != 'yes'):
    found.append ('the package is not registered.')
  for part in parts:
    entry = re.search (r'URL:\s*\S*/%s\s+is registered:\s*(\S+)'
                       % re.escape (part), listing)
    if (not entry):
      found.append ('%s is not listed.' % part)
    elif (entry.group (1) != 'yes'):
      found.append ('%s is not registered.' % part)
  return found


def check (program, package, identifier, version, parts):
  """Install PACKAGE with PROGRAM into a new profile, and return what is
  wrong with the result, one line each, empty where nothing is."""
  folder = tempfile.mkdtemp (prefix = 'octave-calc-profile-')
  profile = pathlib.Path (folder).as_uri ()
  try:
    status, said = unopkg (program, profile, 'add', package)
    print (said, end = '')
    if (status != 0):
      return ['unopkg add failed with exit status %d.' % status]
    status, listing = unopkg (program, profile, 'list', identifier)
    print (listing, end = '')
    if (status != 0):
      return ['unopkg list failed with exit status %d.' % status]
    return problems (listing, identifier, version, parts)
  finally:
    shutil.rmtree (folder, ignore_errors = True)


if (__name__ == '__main__'):
  if (len (sys.argv) != 3):
    sys.exit ('usage: check_install.py UNOPKG PACKAGE')
  program, package = sys.argv[1:]
  identifier, version, parts = declared (package)
  found = check (program, package, identifier, version, parts)
  for problem in found:
    print ('FAIL  %s' % problem)
  if (found):
    sys.exit (1)
  print ('PASS  %s %s installed, %d parts registered.'
         % (identifier, version, len (parts)))
