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
## @deftypefn {octave-calc} {@var{C} =} octave_calc_ff2n (@var{FACTORS})
##
## Two-level factorial design for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_ff2n (@var{FACTORS})} lays out every
## combination of two levels, 0 and 1, of @var{FACTORS} factors, one run per
## row.  @var{FACTORS} is a whole number from 1 to 15, each factor doubling
## the number of runs.
##
## @var{C} is a cell array of scalars and text, laid out as the cells written
## into the sheet: the title, the number of runs, then a heading of
## @qcode{'Run'} and one column per factor, and a row per run.
##
## The @code{statistics} package must be loaded.
##
## @seealso{ff2n, fullfact}
## @end deftypefn

function C = octave_calc_ff2n (FACTORS)

  ## Input validation
  if (nargin != 1)
    error ("octave_calc_ff2n: invalid number of input arguments.");
  endif
  if (! (isnumeric (FACTORS) && isreal (FACTORS) && isscalar (FACTORS)
         && FACTORS == fix (FACTORS) && FACTORS >= 1 && FACTORS <= 15))
    error (strcat ("octave_calc_ff2n: FACTORS must be a whole number", ...
                   " from 1 to 15."));
  endif

  A = ff2n (FACTORS);
  k = columns (A);
  heading = [{'Run'}, arrayfun(@(ii) sprintf ("Factor %d", ii), 1:k, ...
                               "UniformOutput", false)];
  runs = [num2cell((1:rows (A))'), num2cell(A)];
  C = [[{'Two-level factorial design'}, cell(1, k)]; ...
       [{'Runs'}, {rows(A)}, cell(1, k - 1)]; cell(1, k + 1); ...
       heading; runs];

endfunction

%!shared C
%! C = octave_calc_ff2n (3);
%!test
%! assert_equal (size (C), [12, 4]);
%!test
%! assert_equal (C(1,1), {'Two-level factorial design'});
%!test
%! assert_equal (C(2,1:2), {'Runs', 8});
%!test
%! assert_equal (C(4,:), {'Run', 'Factor 1', 'Factor 2', 'Factor 3'});
%!test
%! assert_equal (C(5,:), {1, 0, 0, 0});
%!test
%! assert_equal (C(12,:), {8, 1, 1, 1});
%!test
%! R = octave_calc_ff2n (1);
%! assert_equal (size (R), [6, 2]);

%!error<octave_calc_ff2n: invalid number of input arguments.> ...
%! octave_calc_ff2n ()
%!error<octave_calc_ff2n: FACTORS must be a whole number from 1 to 15.> ...
%! octave_calc_ff2n (0)
%!error<octave_calc_ff2n: FACTORS must be a whole number from 1 to 15.> ...
%! octave_calc_ff2n (2.5)
%!error<octave_calc_ff2n: FACTORS must be a whole number from 1 to 15.> ...
%! octave_calc_ff2n (16)
