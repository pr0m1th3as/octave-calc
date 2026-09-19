## Copyright (C) 2026 Andreas Bertsatos <abertsatos@biol.uoa.gr>
##
## This file is part of the octave-calc extension.
##
## This program is free software; you can redistribute it and/or modify it under
## the terms of the GNU General Public License as published by the Free Software
## Foundation; either version 3 of the License, or (at your option) any later
## version.
##
## This program is distributed in the hope that it will be useful, but WITHOUT
## ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
## FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
## details.
##
## You should have received a copy of the GNU General Public License along with
## this program; if not, see <http://www.gnu.org/licenses/>.

## -*- texinfo -*-
## @deftypefn {octave-calc} {@var{R} =} octave_calc_dropped (@var{DROPPED})
##
## How an analysis of matched measurements says that it left subjects out,
## for Data > Statistics with GNU Octave.
##
## @var{DROPPED} is how many subjects were missing a measurement and so took
## part in none of them.  @var{R} is the cells that say so, eight columns
## wide: the sentence and a blank line where any were left out, and nothing
## at all where none were, since a count of zero is noise.
##
## @end deftypefn

function R = octave_calc_dropped (DROPPED)

  R = cell (0, 8);
  if (DROPPED < 1)
    return;
  endif
  R = cell (2, 8);
  if (DROPPED == 1)
    R{1,1} = 'One subject was left out for a missing measurement.';
  else
    R{1,1} = sprintf (strcat ("%d subjects were left out for a missing", ...
                              " measurement."), DROPPED);
  endif

endfunction
