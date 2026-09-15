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

"""The Calc Add-In: =OCTAVE("mean"; A1:C2; 2; "omitnan") in a cell.

This file is a declaration with a method attached.  Everything it does is in
octave_core, which knows nothing about LibreOffice and can be tested from a
plain Python prompt.

A formula cannot use a thread: Calc's engine calls and waits for a value, so
this path blocks where the menu-driven workbench does not.  That is why
octave_core memoises, and why a recalculation that changes no input costs
nothing.
"""

import os
import sys

import unohelper

from com.sun.star.lang import XServiceInfo, Locale
from com.sun.star.sheet import XAddIn

sys.path.insert (0, os.path.dirname (os.path.abspath (__file__)))
import octave_core

from org.octavecalc import XOctave

IMPLEMENTATION = 'org.octavecalc.OctaveImpl'
SERVICE = 'org.octavecalc.Octave'
ADDIN = 'com.sun.star.sheet.AddIn'

# Display name in a cell, against the method name in the interface.  The .xcu
# declares the same pairing, and Calc consults both.
FUNCTIONS = {'OCTAVE': 'run'}

ARGUMENTS = {'run': (('name', 'Name of the Octave function to run.'),
                     ('data', 'Range of cells it runs over.'),
                     ('args', 'Further arguments, such as 2 or "omitnan".'))}


class Octave (unohelper.Base, XOctave, XAddIn, XServiceInfo):

  def __init__ (self, ctx):
    self.ctx = ctx
    self.locale = Locale ('en', 'US', '')

  # The function.
  def run (self, name, data, args):
    return octave_core.call (name, data, args)

  # XAddIn.  The API's own spelling of Funtion is not a typo here.
  def getProgrammaticFuntionName (self, display):
    return FUNCTIONS.get (display, '')

  def getDisplayFunctionName (self, name):
    for display, programmatic in FUNCTIONS.items ():
      if (programmatic == name):
        return display
    return ''

  def getFunctionDescription (self, name):
    if (name == 'run'):
      return 'Runs an Octave function over a range and returns its result.'
    return ''

  def getDisplayArgumentName (self, name, index):
    arguments = ARGUMENTS.get (name, ())
    return arguments[index][0] if index < len (arguments) else ''

  def getArgumentDescription (self, name, index):
    arguments = ARGUMENTS.get (name, ())
    return arguments[index][1] if index < len (arguments) else ''

  def getProgrammaticCategoryName (self, name):
    return 'Add-In'

  def getDisplayCategoryName (self, name):
    return 'Add-In'

  # XLocalizable, which XAddIn extends.
  def setLocale (self, locale):
    self.locale = locale

  def getLocale (self):
    return self.locale

  # XServiceInfo.
  def getImplementationName (self):
    return IMPLEMENTATION

  def supportsService (self, name):
    return name in (SERVICE, ADDIN)

  def getSupportedServiceNames (self):
    return (SERVICE, ADDIN)


g_ImplementationHelper = unohelper.ImplementationHelper ()
g_ImplementationHelper.addImplementation (Octave, IMPLEMENTATION,
                                          (SERVICE, ADDIN))
