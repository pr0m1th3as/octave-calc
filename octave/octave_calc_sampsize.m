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
## @deftypefn {octave-calc} {@var{C} =} octave_calc_sampsize (@var{TESTTYPE}, @var{NULLVALUE}, @var{NULLSD}, @var{P1}, @var{POWER}, @var{ALPHA})
##
## Sample size for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_sampsize (@var{TESTTYPE}, @var{NULLVALUE},
## @var{NULLSD}, @var{P1}, @var{POWER}, @var{ALPHA})} gives the number of
## observations a test needs to reach @var{POWER} against the alternative
## @var{P1}, at the significance level @var{ALPHA}.  @var{NULLSD} is taken by
## @qcode{'z'}, @qcode{'t'} and @qcode{'t2'} and ignored by the rest.
##
## @var{C} is a cell array two columns wide, laid out as the cells written into
## the sheet: what was given, then the sample size, which the two-sample t-test
## reports for each group.
##
## The @code{statistics} package must be loaded.
##
## @seealso{sampsizepwr}
## @end deftypefn

function C = octave_calc_sampsize (TESTTYPE, NULLVALUE, NULLSD, P1, POWER, ...
                                   ALPHA)

  if (nargin != 6)
    error ("octave_calc_sampsize: invalid number of input arguments.");
  endif
  [rows, errmsg] = octave_calc_sampsizepwr ('n', TESTTYPE, NULLVALUE, ...
                                            NULLSD, P1, POWER, [], ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_sampsize: %s", errmsg);
  endif
  C = [{'Sample size', []}; cell(1, 2); rows];

endfunction

%!shared C
%! C = octave_calc_sampsize ('t', 5, 2, 6, 0.9, 0.05);
%!test
%! assert_equal (C(1,1), {'Sample size'});
%!test
%! assert_equal (C(3,:), {'Test', 'one-sample or paired t-test'});
%!test
%! assert_equal (C(4,:), {'Null value', 5});
%!test
%! assert_equal (C(5,:), {'Null standard deviation', 2});
%!test
%! assert_equal (C(end,:), {'Sample size', sampsizepwr('t', [5 2], 6, 0.9)});
%!test
%! R = octave_calc_sampsize ('t2', 5, 2, 6, 0.9, 0.05);
%! assert_equal (R(end-1:end,1), {'Sample size, first group'; ...
%!                                'Sample size, second group'});
%!test
%! ## A test of a proportion ignores the standard deviation
%! R = octave_calc_sampsize ('p', 0.3, 2, 0.4, 0.8, 0.05);
%! assert_equal (R(end,:), {'Sample size', sampsizepwr('p', 0.3, 0.4, 0.8)});

%!error<octave_calc_sampsize: invalid number of input arguments.> ...
%! octave_calc_sampsize ('t', 5, 2, 6, 0.9)
%!error<octave_calc_sampsize: TESTTYPE must be 'z', 't', 't2', 'var', 'p' or 'r'.> ...
%! octave_calc_sampsize ('f', 5, 2, 6, 0.9, 0.05)
%!error<octave_calc_sampsize: the null standard deviation must be a number greater than 0.> ...
%! octave_calc_sampsize ('t', 5, 0, 6, 0.9, 0.05)
%!error<octave_calc_sampsize: the power must be a number greater than 0 and less than 1.> ...
%! octave_calc_sampsize ('t', 5, 2, 6, 1, 0.05)
%!error<octave_calc_sampsize: the significance level must be a number greater than 0 and less than 1.> ...
%! octave_calc_sampsize ('t', 5, 2, 6, 0.9, 0)
