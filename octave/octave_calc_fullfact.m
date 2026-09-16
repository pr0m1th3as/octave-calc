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
## @deftypefn {octave-calc} {@var{C} =} octave_calc_fullfact (@var{LEVELS})
##
## Full factorial design for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_fullfact (@var{LEVELS})} lays out every
## combination of the levels of each factor, one run per row, from
## @var{LEVELS}, a vector holding the number of levels of each factor, each a
## whole number of 2 or more.
##
## @var{C} is a cell array of scalars and text, laid out as the cells written
## into the sheet: the title, the number of runs, then a heading of
## @qcode{'Run'} and one column per factor, and a row per run.
##
## The @code{statistics} package must be loaded.
##
## @seealso{fullfact, ff2n}
## @end deftypefn

function C = octave_calc_fullfact (LEVELS)

  ## Input validation
  if (nargin != 1)
    error ("octave_calc_fullfact: invalid number of input arguments.");
  endif
  if (! (isnumeric (LEVELS) && isreal (LEVELS) && isvector (LEVELS)
         && ! isempty (LEVELS) && all (LEVELS == fix (LEVELS))
         && all (LEVELS >= 2)))
    error (strcat ("octave_calc_fullfact: LEVELS must hold one whole", ...
                   " number of 2 or more for each factor."));
  endif

  A = fullfact (LEVELS(:).');
  k = columns (A);
  heading = [{'Run'}, arrayfun(@(ii) sprintf ("Factor %d", ii), 1:k, ...
                               "UniformOutput", false)];
  runs = [num2cell((1:rows (A))'), num2cell(A)];
  C = [[{'Full factorial design'}, cell(1, k)]; ...
       [{'Runs'}, {rows(A)}, cell(1, k - 1)]; cell(1, k + 1); ...
       heading; runs];

endfunction

%!shared C
%! C = octave_calc_fullfact ([2, 3]);
%!test
%! assert_equal (size (C), [10, 3]);
%!test
%! assert_equal (C(1,1), {'Full factorial design'});
%!test
%! assert_equal (C(2,1:2), {'Runs', 6});
%!test
%! assert_equal (C(4,:), {'Run', 'Factor 1', 'Factor 2'});
%!test
%! assert_equal (C(5,:), {1, 1, 1});
%!test
%! assert_equal (C(10,:), {6, 2, 3});
%!test
%! R = octave_calc_fullfact ([2, 2, 2]);
%! assert_equal (size (R), [12, 4]);

%!error<octave_calc_fullfact: invalid number of input arguments.> ...
%! octave_calc_fullfact ()
%!error<octave_calc_fullfact: LEVELS must hold one whole number of 2 or more for each factor.> ...
%! octave_calc_fullfact ([2, 1])
%!error<octave_calc_fullfact: LEVELS must hold one whole number of 2 or more for each factor.> ...
%! octave_calc_fullfact ([2, 2.5])
%!error<octave_calc_fullfact: LEVELS must hold one whole number of 2 or more for each factor.> ...
%! octave_calc_fullfact ('ab')
