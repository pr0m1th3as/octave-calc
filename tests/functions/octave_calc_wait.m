## Copyright (C) 2026 Andreas Bertsatos <abertsatos@biol.uoa.gr>
##
## This file is part of the octave-calc extension.
##
## This program is free software: you can redistribute it and/or modify it
## under the terms of the GNU General Public License as published by the Free
## Software Foundation, either version 3 of the License, or (at your option)
## any later version.
##
## This program is distributed in the hope that it will be useful, but WITHOUT
## ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
## FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
## more details.
##
## You should have received a copy of the GNU General Public License along
## with this program.  If not, see <https://www.gnu.org/licenses/>.

## -*- texinfo -*-
## @deftypefn {octave-calc} {@var{s} =} octave_calc_wait (@var{s})
##
## Wait @var{s} seconds, then return @var{s}.  A fixture for the tests of
## @file{octave_core.py}, which use it to reach a server's deadline.
##
## @end deftypefn

function s = octave_calc_wait (s)
  pause (s);
endfunction

%!test
%! assert_equal (octave_calc_wait (0), 0);
