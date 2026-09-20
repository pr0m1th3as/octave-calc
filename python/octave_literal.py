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

"""What a Custom analysis field holds when it is not a range: an Octave
literal, read here and never evaluated.

The reading is done when the user presses OK, so a mistake is named in the
dialog before anything is called, and octave_call is still given values and
never text to run.  Nothing here makes a UNO call.

A literal is a number, Inf or NaN; text in quotes; true or false; []; a
matrix of numbers; or a range.  A name, a call, an expression and pi are all
refused, and so is a transpose in any form: a transpose is an operation and
not a literal, so a column is typed with semicolons.
"""

import math
import re

import octave_core

# The most elements a typed matrix or range may hold.
MAX_ELEMENTS = 1000000

# What a field takes, ending a refusal.
ACCEPTS = ('a number, Inf or NaN; text in quotes; true or false; []; a '
           'matrix such as [1, 2; 3, 4]; or a range such as 1:5 or 0:0.1:1')

UNSIGNED = re.compile (r'(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?\Z')

# Octave counts the elements of a range with a tolerance, so that a step it
# cannot hold exactly does not lose the last element: 0:0.1:0.7 holds eight.
TOLERANCE = 3.0 * 2.0 ** -52


def number (token):
  """The number TOKEN holds, or None where it holds no number."""
  body = token.strip ()
  sign = 1.0
  if (body[:1] in ('+', '-')):
    sign = -1.0 if body[0] == '-' else 1.0
    body = body[1:].strip ()
  if (body.lower () == 'inf'):
    return sign * float ('inf')
  if (body.lower () == 'nan'):
    return float ('nan')
  if (UNSIGNED.match (body)):
    return sign * float (body)
  return None


def counted (first, step, last):
  """How many elements the range FIRST:STEP:LAST holds, as Octave counts
  them."""
  if (step == 0 or not all (map (math.isfinite, (first, step, last)))):
    return 0
  reach = (last - first) / step
  if (reach < 0):
    return 0
  return int (math.floor (reach + TOLERANCE * max (abs (reach), 1.0))) + 1


def spread (token):
  """The numbers the range TOKEN holds, or None where it is not a range.
  Raises ValueError where it is one and holds too many."""
  parts = token.split (':')
  if (len (parts) not in (2, 3)):
    return None
  bounds = [number (part) for part in parts]
  if (any (bound is None for bound in bounds)):
    return None
  first, step, last = (bounds[0], 1.0, bounds[1]) if len (bounds) == 2 \
                      else bounds
  held = counted (first, step, last)
  if (held > MAX_ELEMENTS):
    raise ValueError ('the range %s holds %d numbers, and the most a field '
                      'may hold is %d.' % (token.strip (), held,
                                           MAX_ELEMENTS))
  return [first + step * n for n in range (held)]


def quoted (body):
  """The text the quoted BODY holds, or None where it is not quoted.  Two
  quotes of the kind that opened it stand for one."""
  mark = body[:1]
  if (mark not in ("'", '"') or len (body) < 2 or body[-1] != mark):
    return None
  inner = body[1:-1]
  if (inner.replace (mark * 2, '') .count (mark)):
    return None
  return inner.replace (mark * 2, mark)


def elements (row):
  """The numbers a matrix row holds, its ranges spread out."""
  held = []
  for token in row.replace (',', ' ').split ():
    one = number (token)
    if (one is not None):
      held.append (one)
      continue
    many = spread (token)
    if (many is None):
      raise ValueError ('a matrix holds numbers and ranges of numbers; "%s" '
                        'is neither.' % token)
    held.extend (many)
  return held


def matrix (body):
  """The rows of numbers the matrix BODY holds, brackets and all."""
  rows = [elements (row) for row in body[1:-1].split (';')]
  rows = [row for row in rows if row] or []
  if (not rows):
    return []
  width = len (rows[0])
  if (any (len (row) != width for row in rows)):
    raise ValueError ('every row of a matrix must hold the same count of '
                      'numbers.')
  if (width * len (rows) > MAX_ELEMENTS):
    raise ValueError ('the matrix holds %d numbers, and the most a field may '
                      'hold is %d.' % (width * len (rows), MAX_ELEMENTS))
  return rows


def numbers_arg (rows):
  """The octave_call argument for ROWS of numbers."""
  if (not rows):
    return {'type': 'range', 'rows': 0, 'cols': 0, 'cells': []}
  return octave_core.range_arg (
    [[{'kind': 'number', 'value': value} for value in row] for row in rows])


def parse (text):
  """The octave_call argument the literal TEXT holds.  Raises ValueError
  saying what is wrong, never what the field should have been instead, since
  a field that is not a literal is read as a range reference."""
  body = text.strip ()
  if (not body):
    raise ValueError ('it is empty.')
  if (body[0] not in ("'", '"') and body[-1] == "'"):
    raise ValueError ('a transpose is an operation and not a literal, so it '
                      'cannot be typed here.  Type a column with semicolons, '
                      '[1; 2; 3].')
  if ('(' in body or ')' in body):
    raise ValueError ('a field holds %s, and no parentheses.' % ACCEPTS)
  held = quoted (body)
  if (held is not None):
    return {'type': 'string', 'value': held}
  if (body.lower () in ('true', 'false')):
    return {'type': 'logical', 'value': body.lower () == 'true'}
  one = number (body)
  if (one is not None):
    return {'type': 'number', 'value': one}
  many = spread (body)
  if (many is not None):
    return numbers_arg ([many] if many else [])
  if (body[0] == '[' and body[-1] == ']'):
    return numbers_arg (matrix (body))
  raise ValueError ('a field holds %s.' % ACCEPTS)


def pairs (text):
  """The octave_call arguments the cell literal TEXT holds, a name and a
  value each.  Raises ValueError."""
  body = text.strip ()
  if (not (body[:1] == '{' and body[-1:] == '}')):
    raise ValueError ('name and value pairs are typed as a cell, such as '
                      "{'Name', 2.3, 'Next', [2, 3]}.")
  held = split (body[1:-1])
  if (len (held) % 2):
    raise ValueError ('name and value pairs must be even in number; %d were '
                      'given.' % len (held))
  args = []
  for place, item in enumerate (held):
    if (place % 2 == 0 and quoted (item.strip ()) is None):
      raise ValueError ('the name of a pair must be text in quotes; "%s" is '
                        'not.' % item.strip ())
    if (place % 2 and item.strip ()[:1] == '{'):
      raise ValueError ('the value of a pair cannot itself be a cell.')
    args.append (parse (item))
  return args


def split (body):
  """The items of a cell literal's BODY, on the commas that are not inside
  quotes or brackets."""
  items, depth, mark, held = [], 0, '', ''
  for letter in body:
    if (mark):
      held += letter
      if (letter == mark):
        mark = ''
      continue
    if (letter in ("'", '"')):
      mark = letter
    elif (letter in '[{'):
      depth += 1
    elif (letter in ']}'):
      depth -= 1
    elif (letter == ',' and depth == 0):
      items.append (held)
      held = ''
      continue
    held += letter
  if (held.strip ()):
    items.append (held)
  return items
