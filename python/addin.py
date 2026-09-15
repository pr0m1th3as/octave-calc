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
from com.sun.star.awt import XCallback
from com.sun.star.sheet.FormulaResult import STRING as RESULT_STRING

sys.path.insert (0, os.path.dirname (os.path.abspath (__file__)))
import octave_core
import octave_settings

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
  return octave_core.numeric_texts (rows)


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


# Format codes are made with English keywords, so they are added under an
# English locale whatever the document's language.
ENGLISH = Locale ('en', 'US', '')


def format_key (formats, code):
  key = formats.queryKey (code, ENGLISH, False)
  if (key == -1):
    key = formats.addNew (code, ENGLISH)
  return key


def label_sheet (sheet, formats):
  """Show every cell of SHEET holding an OCTRANGE key as its range's label,
  and return a cell that no longer holds one to the default format.  A cell
  the user formatted is left alone."""
  wanted = {}
  found = sheet.queryFormulaCells (RESULT_STRING)
  for area in found.getRangeAddresses ():
    block = sheet.getCellRangeByPosition (area.StartColumn, area.StartRow,
                                          area.EndColumn, area.EndRow)
    for r, values in enumerate (block.getDataArray ()):
      for c, value in enumerate (values):
        if (isinstance (value, str) and octave_core.key_parts (value)):
          wanted[(area.StartColumn + c, area.StartRow + r)] = (
            octave_core.range_label (value, sheet.Name))

  labelled = {}
  parts = sheet.getCellFormatRanges ()
  for index in range (parts.Count):
    part = parts.getByIndex (index)
    shown = octave_core.label_of_format (
      formats.getByKey (part.NumberFormat).FormatString)
    if (shown is None):
      continue
    area = part.getRangeAddress ()
    for row in range (area.StartRow, area.EndRow + 1):
      for column in range (area.StartColumn, area.EndColumn + 1):
        labelled[(column, row)] = shown

  for (column, row) in labelled:
    if ((column, row) not in wanted):
      sheet.getCellByPosition (column, row).NumberFormat = 0
  for (column, row), label in wanted.items ():
    cell = sheet.getCellByPosition (column, row)
    # Compared as labels, since Calc rewrites the code it was given
    if ((column, row) in labelled):
      if (labelled[(column, row)] == label):
        continue
    elif (cell.NumberFormat % 10000 != 0):
      continue
    cell.NumberFormat = format_key (formats, octave_core.label_format (label))


def label_document (document):
  """Label every sheet of DOCUMENT, invisibly to its undo history and without
  marking an unmodified document modified."""
  undo = document.getUndoManager ()
  modified = document.isModified ()
  undo.lock ()
  try:
    for index in range (document.Sheets.Count):
      label_sheet (document.Sheets.getByIndex (index), document.NumberFormats)
  finally:
    undo.unlock ()
    if (not modified and document.isModified ()):
      document.setModified (False)


class LabelPass (unohelper.Base, XCallback):
  """Labels OCTRANGE cells on the main thread once calculation is over, since
  an Add-In is not told which cell called it.  Every OCTRANGE call of one
  calculation shares a single pass."""

  def __init__ (self):
    self.documents = []
    self.scheduled = False

  def request (self, ctx, document):
    if (not any (document == known for known in self.documents)):
      self.documents.append (document)
    if (not self.scheduled):
      self.scheduled = True
      ctx.ServiceManager.createInstanceWithContext (
        'com.sun.star.awt.AsyncCallback', ctx).addCallback (self, None)

  def notify (self, unused):
    documents, self.documents, self.scheduled = self.documents, [], False
    for document in documents:
      try:
        label_document (document)
      except Exception:
        # A caller that is not a spreadsheet document, or one closed since
        pass


LABELS = LabelPass ()


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
      runner = octave_core.server ('cell',
                                   octave_settings.read (self.ctx, 'cell'))
    except Exception as err:
      return ((octave_core.MESSAGE_PREFIX + str (err),),)
    return octave_core.call (name, built, null_date (caller), runner)

  def octrange (self, caller, data, mode):
    try:
      mode = octave_core.range_mode (mode)
      address = data.getRangeAddress ()
      rows = read_range (caller, data)
      key = octave_core.range_key (mode, data.AbsoluteName, rows)
      octave_core.remember_range (key, address.StartColumn, address.StartRow,
                                  rows)
      LABELS.request (self.ctx, caller)
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
