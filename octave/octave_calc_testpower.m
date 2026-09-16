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
## @deftypefn {octave-calc} {@var{C} =} octave_calc_testpower (@var{TESTTYPE}, @var{NULLVALUE}, @var{NULLSD}, @var{P1}, @var{N}, @var{ALPHA})
##
## Power for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_testpower (@var{TESTTYPE}, @var{NULLVALUE},
## @var{NULLSD}, @var{P1}, @var{N}, @var{ALPHA})} gives the power a test of
## @var{N} observations has against the alternative @var{P1}, at the
## significance level @var{ALPHA}.  @var{NULLSD} is taken by @qcode{'z'},
## @qcode{'t'} and @qcode{'t2'} and ignored by the rest.
##
## @var{C} is a cell array two columns wide, laid out as the cells written into
## the sheet: what was given, then the power.
##
## The @code{statistics} package must be loaded.
##
## @seealso{sampsizepwr}
## @end deftypefn

function C = octave_calc_testpower (TESTTYPE, NULLVALUE, NULLSD, P1, N, ALPHA)

  if (nargin != 6)
    error ("octave_calc_testpower: invalid number of input arguments.");
  endif
  [rows, errmsg] = octave_calc_sampsizepwr ('power', TESTTYPE, NULLVALUE, ...
                                            NULLSD, P1, [], N, ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_testpower: %s", errmsg);
  endif
  C = [{'Power', []}; cell(1, 2); rows];

endfunction

%!shared C
%! C = octave_calc_testpower ('t', 5, 2, 6, 30, 0.05);
%!test
%! assert_equal (C(1,1), {'Power'});
%!test
%! assert_equal (C(3,:), {'Test', 'one-sample or paired t-test'});
%!test
%! assert_equal (C(7,:), {'Sample size', 30});
%!test
%! assert_equal (C(end,:), ...
%!               {'Power', sampsizepwr('t', [5 2], 6, [], 30)});
%!test
%! R = octave_calc_testpower ('p', 0.3, 2, 0.4, 100, 0.05);
%! assert_equal (R(end,:), {'Power', sampsizepwr('p', 0.3, 0.4, [], 100)});

%!error<octave_calc_testpower: invalid number of input arguments.> ...
%! octave_calc_testpower ('t', 5, 2, 6, 30)
%!error<octave_calc_testpower: TESTTYPE must be 'z', 't', 't2', 'var', 'p' or 'r'.> ...
%! octave_calc_testpower ('f', 5, 2, 6, 30, 0.05)
%!error<octave_calc_testpower: the sample size must be a whole number of 2 or more.> ...
%! octave_calc_testpower ('t', 5, 2, 6, 1, 0.05)
%!error<octave_calc_testpower: the sample size must be a whole number of 2 or more.> ...
%! octave_calc_testpower ('t', 5, 2, 6, 30.5, 0.05)
%!error<octave_calc_testpower: the alternative value must be a number.> ...
%! octave_calc_testpower ('t', 5, 2, 'x', 30, 0.05)
