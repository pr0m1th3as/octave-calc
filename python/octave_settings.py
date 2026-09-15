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

"""The extension's settings, read from its configuration schema.

They live in LibreOffice's configuration under org.octavecalc.Settings, where
no document can reach them, and are edited through Tools > Options > Advanced
> Expert Configuration.  This is the only place that reads them.
"""

from com.sun.star.beans import PropertyValue

NODE = '/org.octavecalc.Settings'

# The deadline each server role takes.
SECONDS = {'cell': 'CellSeconds', 'workbench': 'WorkbenchSeconds'}


def read (ctx, role):
  """The Server settings for ROLE, 'cell' or 'workbench', as octave_core.Server
  takes them."""
  provider = ctx.ServiceManager.createInstanceWithContext (
    'com.sun.star.configuration.ConfigurationProvider', ctx)
  path = PropertyValue ()
  path.Name = 'nodepath'
  path.Value = NODE
  access = provider.createInstanceWithArguments (
    'com.sun.star.configuration.ConfigurationAccess', (path,))
  return {'folders': list (access.getByName ('Folders') or ()),
          'packages': list (access.getByName ('Packages') or ()),
          'memory': int (access.getByName ('MemoryGB')),
          'tmp': int (access.getByName ('TmpGB')),
          'seconds': int (access.getByName (SECONDS[role]))}
