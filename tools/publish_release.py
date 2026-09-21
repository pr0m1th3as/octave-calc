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

"""Publish what a release serves, from the one place each thing is written.

RELEASE_NOTES holds the notes for the release being prepared and is rewritten
for the next one.  It is the maintainer's working copy and is not in the
repository: what the public reads is docs/, which this writes.  Anyone
without it can still build, test and install; only publishing needs it.

description.xml holds the version.  This copies the notes into docs/, where
Pages serves them and the Extension Manager reads them before offering an
update, and rewrites the update feed to the version and the package the
build makes.

Run it after bumping the version and writing the notes, and before tagging:

  python3 tools/publish_release.py            write docs/ from the sources
  python3 tools/publish_release.py --check    say what would change, write
                                              nothing
"""

import io
import os
import re
import sys

HERE = os.path.dirname (os.path.dirname (os.path.abspath (__file__)))
NOTES = os.path.join (HERE, 'RELEASE_NOTES')
DOCS = os.path.join (HERE, 'docs')
DESCRIPTION = os.path.join (HERE, 'oxt', 'description.xml')

PUBLISHED_NOTES = os.path.join (DOCS, 'release-notes-en.txt')
FEED = os.path.join (DOCS, 'octave-calc.update.xml')

# The tag a release is cut under, and the asset the build leaves in dist/.
TAG = 'v%s'
PACKAGE = 'octave-calc-%s.oxt'
DOWNLOAD = ('https://github.com/pr0m1th3as/octave-calc/releases/download/'
            '%s/%s')

IDENTIFIER = 'io.github.pr0m1th3as.octavecalc'

FEED_TEXT = '''<?xml version="1.0" encoding="UTF-8"?>
<description xmlns="http://openoffice.org/extensions/description/2006"
             xmlns:xlink="http://www.w3.org/1999/xlink">
 <identifier value="%(identifier)s"/>
 <version value="%(version)s"/>
 <update-download>
  <src xlink:href="%(download)s"/>
 </update-download>
 <release-notes>
  <src xlink:href="%(notes)s"
       lang="en"/>
 </release-notes>
</description>
'''

NOTES_URL = 'https://pr0m1th3as.github.io/octave-calc/release-notes-en.txt'


def read (path):
  with io.open (path, encoding = 'utf-8') as held:
    return held.read ()


def version ():
  found = re.search (r'<version\s+value\s*=\s*"([^"]+)"', read (DESCRIPTION))
  if (not found):
    sys.exit ('no version in %s' % DESCRIPTION)
  return found.group (1)


def wanted ():
  """Every published file against what it should hold.  Raises OSError
  where RELEASE_NOTES is absent, this being a working copy the repository
  does not carry."""
  held = version ()
  notes = read (NOTES)
  if (held not in notes.split ('\n', 1)[0]):
    sys.exit ('RELEASE_NOTES does not open on version %s; it reads "%s"'
              % (held, notes.split ('\n', 1)[0].strip ()))
  return {PUBLISHED_NOTES: notes,
          FEED: FEED_TEXT % {'identifier': IDENTIFIER, 'version': held,
                             'notes': NOTES_URL,
                             'download': DOWNLOAD % (TAG % held,
                                                     PACKAGE % held)}}


def main (check):
  if (not os.path.exists (NOTES)):
    sys.exit ('no %s.  It is the maintainer\'s working copy of the notes '
              'for the release being prepared, and is not in the '
              'repository; write it before publishing.'
              % os.path.relpath (NOTES, HERE))
  stale = []
  for path, text in wanted ().items ():
    at = os.path.relpath (path, HERE)
    if (os.path.exists (path) and read (path) == text):
      print ('same    %s' % at)
      continue
    stale.append (at)
    if (check):
      print ('STALE   %s' % at)
      continue
    with io.open (path, 'w', encoding = 'utf-8') as out:
      out.write (text)
    print ('written %s' % at)
  if (check and stale):
    sys.exit ('%d file(s) behind the sources; run without --check'
              % len (stale))


if (__name__ == '__main__'):
  main ('--check' in sys.argv)
