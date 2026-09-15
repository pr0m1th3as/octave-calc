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

This file is a declaration with a method attached, which reads the range cell
by cell.  Everything else it does is in octave_core, which knows nothing about
LibreOffice and can be tested from a plain Python prompt.

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
FUNCTIONS = {'OCTAVE': 'run', 'OCTRANGE': 'octrange'}

DESCRIPTIONS = {
  'run': 'Runs an Octave function on its arguments and returns its result.',
  'octrange': ('Marks a range for OCTAVE so that its dates, times, logical '
               'values and errors keep their kind, as one argument or as '
               'name-value pairs.')}

ARGUMENT = ('Argument of the Octave function: a number, text, a range, or '
            'OCTRANGE of a range whose dates, times or logical values matter.')

# Indexed over every parameter of the method, the hidden caller included, as
# Calc asks for them.
ARGUMENTS = {
  'run': ((('caller', ''), ('name', 'Name of the Octave function to run.'))
          + tuple (('arg%d' % i, ARGUMENT)
                   for i in range (1, octave_core.MAX_ARGS + 1))),
  'octrange': (('caller', ''),
               ('range', 'Range of cells, given as a reference.'),
               ('mode', ('How OCTAVE uses the range: "data", the default, as '
                         'one argument, or "pairs", as name-value arguments '
                         'from two columns, name then value.')))}


def read_range (caller, data):
  """Each cell of DATA as octave_core.cell_kind reads it, row by row.  A caller
  without number formats, such as FunctionAccess, leaves every value a
  number.

  Text comes from getDataArray, which reads a formula's result.  getString
  returns '...' for every formula cell while Calc's interpreter runs, and an
  Add-In always runs inside it."""
  address = data.getRangeAddress ()
  values = data.getDataArray ()
  formats = {}

  def describe (key):
    if (key not in formats):
      try:
        found = caller.NumberFormats.getByKey (key)
        formats[key] = (found.Type, found.FormatString)
      except Exception:
        formats[key] = (0, '')
    return formats[key]

  rows = []
  for r in range (address.EndRow - address.StartRow + 1):
    row = []
    for c in range (address.EndColumn - address.StartColumn + 1):
      cell = data.getCellByPosition (c, r)
      content = cell.getType ().value
      result = cell.FormulaResultType2 if content == 'FORMULA' else 0
      format_type, format_string = describe (cell.NumberFormat)
      shown = values[r][c]
      row.append (octave_core.cell_kind (content, result, cell.getError (),
                                         cell.getValue (),
                                         shown if isinstance (shown, str)
                                         else '',
                                         format_type, format_string))
    rows.append (row)
  return rows


def resolve (caller, key):
  """The top-left column and row and the cells of the range behind an OCTRANGE
  key: those kept in memory, or the range read again from the address in the
  key when its cells still match the digest."""
  found = octave_core.recall_range (key)
  if (found):
    return found
  parts = octave_core.key_parts (key)
  if (parts is None):
    raise ValueError ('"%s" is not an OCTRANGE key.' % key)
  mode, address = parts
  try:
    data = caller.Sheets.getCellRangesByName (address)[0]
  except Exception:
    raise ValueError ('the range %s is not in this document.' % address)
  rows = read_range (caller, data)
  if (octave_core.range_key (mode, address, rows) != key):
    raise ValueError ('the range %s has changed since OCTRANGE read it.  '
                      'Press Ctrl+Shift+F9 to recalculate.' % address)
  where = data.getRangeAddress ()
  octave_core.remember_range (key, where.StartColumn, where.StartRow, rows)
  return where.StartColumn, where.StartRow, rows


def null_date (caller):
  try:
    return octave_core.iso_date (caller.NullDate)
  except Exception:
    return octave_core.NULL_DATE


class Octave (unohelper.Base, XOctave, XAddIn, XServiceInfo):

  def __init__ (self, ctx):
    self.ctx = ctx
    self.locale = Locale ('en', 'US', '')

  # The functions.
  def run (self, caller, name, *args):
    try:
      built = octave_core.build_args (args, lambda key: resolve (caller, key))
    except Exception as err:
      return ((octave_core.MESSAGE_PREFIX + str (err),),)
    return octave_core.call (name, built, null_date (caller))

  def octrange (self, caller, data, mode):
    try:
      mode = octave_core.range_mode (mode)
      address = data.getRangeAddress ()
      rows = read_range (caller, data)
      key = octave_core.range_key (mode, data.AbsoluteName, rows)
      octave_core.remember_range (key, address.StartColumn, address.StartRow,
                                  rows)
      return key
    except Exception as err:
      return octave_core.MESSAGE_PREFIX + str (err)

  # XAddIn.  The API's own spelling of Funtion is not a typo here.
  def getProgrammaticFuntionName (self, display):
    return FUNCTIONS.get (display, '')

  def getDisplayFunctionName (self, name):
    for display, programmatic in FUNCTIONS.items ():
      if (programmatic == name):
        return display
    return ''

  def getFunctionDescription (self, name):
    return DESCRIPTIONS.get (name, '')

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
