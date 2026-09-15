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
## @deftypefn {octave-calc} {@var{y} =} octave_calc_twice (@var{x})
##
## Return twice @var{x}.  A fixture for the tests of @file{octave_core.py},
## reached only as a function in a designated folder inside the sandbox.
##
## @end deftypefn

function y = octave_calc_twice (x)
  y = 2 * x;
endfunction

%!test
%! assert_equal (octave_calc_twice (2), 4);
