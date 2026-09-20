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
## @deftypefn {octave-calc} {@var{N} =} octave_calc_spread (@var{FIRST}, @var{STEP}, @var{LAST})
##
## Return how many numbers the range @var{FIRST}:@var{STEP}:@var{LAST} holds.
## A fixture for the tests of @file{octave_literal.py}, which counts the
## elements of a typed range itself and must count them as Octave does, a
## step it cannot hold exactly otherwise losing the last one.
##
## @end deftypefn

function N = octave_calc_spread (FIRST, STEP, LAST)
  N = numel (FIRST:STEP:LAST);
endfunction

%!test
%! assert_equal (octave_calc_spread (0, 0.1, 0.7), 8);
%!test
%! assert_equal (octave_calc_spread (1, 1, 5), 5);
