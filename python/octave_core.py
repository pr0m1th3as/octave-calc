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

"""Running Octave, and nothing about LibreOffice.

Everything here is testable from a plain Python prompt, which is the point:
the office-facing files hold no logic worth testing and this file holds no UNO
call.  It is shared by the Add-In component and the menu-driven workbench.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile

OCTAVE_CANDIDATES = ('octave-cli', 'octave')

# A bare function name, or a namespaced or static-method one: mean, geom.area,
# ClassName.method.  Anything else never reaches the interpreter.
NAME_RE = re.compile (r'^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)*$')

OCTAVE_FLAGS = ('-q', '--no-init-file', '--no-site-file', '--no-history')

# A formula cannot use a thread, so a recalculation blocks.  The cache is what
# makes that bearable: one that changes no input runs no interpreter at all.
_CACHE = {}
_CACHE_ORDER = []
_CACHE_LIMIT = 200


def octave ():
  """Absolute path to an Octave interpreter, or None."""
  for name in OCTAVE_CANDIDATES:
    found = shutil.which (name)
    if (found):
      return found
  return None


def octave_version (binary):
  probe = subprocess.run (list ((binary,) + OCTAVE_FLAGS)
                          + ['--eval', 'disp (version ());'],
                          capture_output = True, text = True, timeout = 60)
  return probe.stdout.strip ()


def as_rows (data):
  """Whatever the office handed over, as a tuple of row tuples."""
  if (not isinstance (data, (list, tuple))):
    return ((data,),)
  if (data and isinstance (data[0], (list, tuple))):
    return tuple (tuple (row) for row in data)
  return (tuple (data),)


def tag_args (args):
  """Values from cells or literals, tagged so the interpreter rebuilds them
  without guessing.  jsondecode reads [2] as a double, ["a"] as a cell and []
  as a double, so an untagged list is not a reliable wire."""
  tagged = []
  for value in args or ():
    if (isinstance (value, str)):
      tagged.append ({'t': 's', 'v': value})
    else:
      tagged.append ({'t': 'n', 'v': float (value)})
  return tagged


def script (in_path, out_path, err_path, name):
  """The code the interpreter runs.  Every path here is one we made, and the
  only value taken from the user is NAME, which matched NAME_RE.  The
  arguments are read out of the file as data and never appear in this text."""
  return (
    "try\n"
    "  __oc_in__ = jsondecode (fileread ('%s'));\n"
    "  __oc_a__ = __oc_in__.args;\n"
    "  __oc_args__ = {};\n"
    "  if (isstruct (__oc_a__))\n"
    "    __oc_args__ = cell (1, numel (__oc_a__));\n"
    "    for __oc_k__ = 1:numel (__oc_a__)\n"
    "      if (strcmp (__oc_a__(__oc_k__).t, 's'))\n"
    "        __oc_args__{__oc_k__} = char (__oc_a__(__oc_k__).v);\n"
    "      else\n"
    "        __oc_args__{__oc_k__} = double (__oc_a__(__oc_k__).v);\n"
    "      endif\n"
    "    endfor\n"
    "  endif\n"
    "  __oc_r__ = %s (__oc_in__.data, __oc_args__{:});\n"
    "  __oc_out__ = struct ('class', class (__oc_r__), "
    "'size', size (__oc_r__), 'data', __oc_r__);\n"
    "  __oc_fid__ = fopen ('%s', 'w');\n"
    "  fwrite (__oc_fid__, jsonencode (__oc_out__));\n"
    "  fclose (__oc_fid__);\n"
    "catch __oc_err__\n"
    "  __oc_fid__ = fopen ('%s', 'w');\n"
    "  fwrite (__oc_fid__, __oc_err__.message);\n"
    "  fclose (__oc_fid__);\n"
    "end\n" % (in_path, name, out_path, err_path))


def reshape (result):
  """Normalise what Octave returned into rows."""
  klass, size, data = result['class'], result['size'], result['data']
  if (klass == 'char'):
    return ((data if isinstance (data, str) else '',),)
  if (not isinstance (data, list)):
    return ((data,),)
  if (data and isinstance (data[0], list)):
    return tuple (tuple (row) for row in data)
  # A flat list is a vector, and jsonencode does not say which way it runs.
  rows = (size + [1, 1])[0]
  if (rows == 1):
    return (tuple (data),)
  return tuple ((value,) for value in data)


def run (name, rows, tagged, timeout = 600):
  """One cold interpreter, synchronously.  Returns rows, or raises."""
  folder = tempfile.mkdtemp (prefix = 'octave-calc-')
  in_path = os.path.join (folder, 'in.json')
  out_path = os.path.join (folder, 'out.json')
  err_path = os.path.join (folder, 'err.txt')
  with open (in_path, 'w') as fid:
    json.dump ({'data': [list (row) for row in rows], 'args': tagged}, fid)
  subprocess.run (list ((octave (),) + OCTAVE_FLAGS)
                  + ['--eval', script (in_path, out_path, err_path, name)],
                  capture_output = True, text = True, timeout = timeout)
  if (os.path.exists (err_path)):
    with open (err_path) as fid:
      raise RuntimeError (fid.read ().strip ().splitlines ()[0])
  if (not os.path.exists (out_path)):
    raise RuntimeError ('%s produced no result' % name)
  with open (out_path) as fid:
    return reshape (json.load (fid))


def call (name, data, args):
  """What a cell asks for: a matrix, always, or one row holding a message.

  Errors come back as text rather than as an error value, because the message
  is the useful part and #VALUE! is not."""
  try:
    if (not isinstance (name, str) or not NAME_RE.match (name)):
      return (('octave-calc: "%s" is not a function name' % name,),)
    if (not octave ()):
      return (('octave-calc: no Octave interpreter on PATH',),)
    rows = as_rows (data)
    tagged = tag_args (args)
    key = (name, rows, tuple ((a['t'], a['v']) for a in tagged))
    if (key in _CACHE):
      return _CACHE[key]
    value = run (name, rows, tagged)
    _CACHE[key] = value
    _CACHE_ORDER.append (key)
    while (len (_CACHE_ORDER) > _CACHE_LIMIT):
      _CACHE.pop (_CACHE_ORDER.pop (0), None)
    return value
  except Exception as err:
    return (('octave-calc: %s' % err,),)


def clear ():
  """Forget every memoised result."""
  _CACHE.clear ()
  del _CACHE_ORDER[:]
