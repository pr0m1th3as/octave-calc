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

"""The extension's settings, read from and written to its configuration
schema.

They live in LibreOffice's configuration under org.octavecalc.Settings, where
no document can reach them, and are edited through Tools > Options > Advanced
> Expert Configuration, or, for the folders and the custom analyses, from the
Statistics menu's own dialog.  This is the only place that touches them.
"""

import uno

from com.sun.star.beans import PropertyValue

NODE = '/org.octavecalc.Settings'

# The deadline each server role takes.
SECONDS = {'cell': 'CellSeconds', 'workbench': 'WorkbenchSeconds'}

# The lists the dialog may edit.  Everything else is Expert Configuration's.
EDITABLE = ('Folders', 'Analyses')


def opened (ctx, service):
  """The settings node, through SERVICE."""
  provider = ctx.ServiceManager.createInstanceWithContext (
    'com.sun.star.configuration.ConfigurationProvider', ctx)
  path = PropertyValue ()
  path.Name = 'nodepath'
  path.Value = NODE
  return provider.createInstanceWithArguments (service, (path,))


def listed (ctx, name):
  """The string list NAME holds, which must be one the dialog may edit."""
  if (name not in EDITABLE):
    raise ValueError ('%s is not a setting this dialog edits.' % name)
  access = opened (ctx, 'com.sun.star.configuration.ConfigurationAccess')
  return list (access.getByName (name) or ())


def relist (ctx, name, values):
  """Put VALUES in the string list NAME and keep them.  Raises where the
  setting is not one the dialog edits."""
  if (name not in EDITABLE):
    raise ValueError ('%s is not a setting this dialog edits.' % name)
  access = opened (ctx,
                   'com.sun.star.configuration.ConfigurationUpdateAccess')
  # The setting is a string list, and a bare Python tuple leaves the type of
  # its elements open, which configmgr refuses as an inappropriate value.
  # An empty one says nothing about its elements at all, so both are sent as
  # a sequence of strings and said to be one.
  uno.invoke (access, 'setPropertyValue',
              (name, uno.Any ('[]string', tuple (str (v) for v in values))))
  access.commitChanges ()


def read (ctx, role):
  """The Server settings for ROLE, 'cell' or 'workbench', as octave_core.Server
  takes them."""
  access = opened (ctx, 'com.sun.star.configuration.ConfigurationAccess')
  return {'folders': list (access.getByName ('Folders') or ()),
          'packages': list (access.getByName ('Packages') or ()),
          'memory': int (access.getByName ('MemoryGB')),
          'tmp': int (access.getByName ('TmpGB')),
          'seconds': int (access.getByName (SECONDS[role]))}
