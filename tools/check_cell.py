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

"""Install a built package into a new LibreOffice profile, start LibreOffice
without a window, and check what a cell holding =OCTAVE("plus";1;1) shows.
The profile is made for the check and removed after it.

Usage:
  PYTHON tools/check_cell.py SOFFICE UNOPKG PACKAGE [--refusal]

PYTHON is one that can import uno: the system python3 where LibreOffice
comes from the distribution, and the one LibreOffice bundles on Windows and
macOS.  Without --refusal the cell must show 2.  With it, the cell must say
that cells run only inside a sandbox, which is what a machine without one
shows, Windows among them.
"""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

import uno

from com.sun.star.connection import NoConnectException
from com.sun.star.sheet.FormulaResult import VALUE

sys.path.insert (0, os.path.dirname (os.path.abspath (__file__)))

import check_install

FORMULA = '=OCTAVE("plus";1;1)'

REFUSAL = 'octave-calc: cells run only inside a sandbox'

# Seconds to wait for LibreOffice to accept a connection, and for the cell,
# whose first call starts an Octave server.
CONNECT_SECONDS = 120


def connect (pipe):
  """The component context of the LibreOffice listening on PIPE."""
  local = uno.getComponentContext ()
  resolver = local.ServiceManager.createInstanceWithContext (
    'com.sun.star.bridge.UnoUrlResolver', local)
  deadline = time.time () + CONNECT_SECONDS
  while (True):
    try:
      return resolver.resolve ('uno:pipe,name=%s;urp;'
                               'StarOffice.ComponentContext' % pipe)
    except NoConnectException:
      if (time.time () > deadline):
        raise
      time.sleep (1)


def hidden ():
  prop = uno.createUnoStruct ('com.sun.star.beans.PropertyValue')
  prop.Name = 'Hidden'
  prop.Value = True
  return (prop,)


def cell_result (soffice, profile):
  """Start SOFFICE on PROFILE, enter the formula in a new sheet, and return
  what the cell shows: its value where it is a number, its text otherwise."""
  pipe = 'octavecalc%d' % os.getpid ()
  office = subprocess.Popen ([soffice, '--headless', '--invisible',
                              '--norestore', '--nologo', '--nodefault',
                              '-env:UserInstallation=' + profile,
                              '--accept=pipe,name=%s;urp;' % pipe])
  try:
    ctx = connect (pipe)
    desktop = ctx.ServiceManager.createInstanceWithContext (
      'com.sun.star.frame.Desktop', ctx)
    document = desktop.loadComponentFromURL ('private:factory/scalc',
                                             '_blank', 0, hidden ())
    cell = document.Sheets.getByIndex (0).getCellByPosition (0, 0)
    cell.setFormula (FORMULA)
    document.calculateAll ()
    if (cell.FormulaResultType2 == VALUE):
      shown = cell.getValue ()
    else:
      shown = cell.getString ()
    document.close (True)
    try:
      desktop.terminate ()
    except Exception:
      pass
    return shown
  finally:
    try:
      office.wait (timeout = 60)
    except subprocess.TimeoutExpired:
      office.kill ()


def check (soffice, program, package, refusal):
  """Install PACKAGE with PROGRAM into a new profile, and return what is
  wrong with the cell, one line each, empty where nothing is."""
  identifier, version, parts = check_install.declared (package)
  folder = tempfile.mkdtemp (prefix = 'octave-calc-profile-')
  profile = pathlib.Path (folder).as_uri ()
  try:
    status, said = check_install.unopkg (program, profile, 'add', package)
    if (status != 0):
      print (said, end = '')
      return ['unopkg add failed with exit status %d.' % status]
    shown = cell_result (soffice, profile)
    print ('%s shows %r' % (FORMULA, shown))
    if (refusal):
      if (not (isinstance (shown, str) and shown.startswith (REFUSAL))):
        return ['the cell does not refuse for want of a sandbox.']
    elif (shown != 2.0):
      return ['the cell does not show 2.']
    return []
  finally:
    shutil.rmtree (folder, ignore_errors = True)


if (__name__ == '__main__'):
  arguments = [word for word in sys.argv[1:] if word != '--refusal']
  if (len (arguments) != 3):
    sys.exit ('usage: check_cell.py SOFFICE UNOPKG PACKAGE [--refusal]')
  found = check (*arguments, refusal = ('--refusal' in sys.argv))
  for problem in found:
    print ('FAIL  %s' % problem)
  if (found):
    sys.exit (1)
  print ('PASS  %s' % ('the cell refuses without a sandbox'
                       if ('--refusal' in sys.argv) else 'the cell shows 2'))
