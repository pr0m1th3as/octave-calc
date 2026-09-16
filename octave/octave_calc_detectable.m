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
## @deftypefn {octave-calc} {@var{C} =} octave_calc_detectable (@var{TESTTYPE}, @var{NULLVALUE}, @var{NULLSD}, @var{POWER}, @var{N}, @var{ALPHA})
##
## Detectable difference for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_detectable (@var{TESTTYPE}, @var{NULLVALUE},
## @var{NULLSD}, @var{POWER}, @var{N}, @var{ALPHA})} gives the value of the
## parameter under the alternative hypothesis that a test of @var{N}
## observations detects with @var{POWER}, at the significance level
## @var{ALPHA}.  @var{NULLSD} is taken by @qcode{'z'}, @qcode{'t'} and
## @qcode{'t2'} and ignored by the rest.
##
## @var{C} is a cell array two columns wide, laid out as the cells written into
## the sheet: what was given, then the detectable value.
##
## The @code{statistics} package must be loaded.
##
## @seealso{sampsizepwr}
## @end deftypefn

function C = octave_calc_detectable (TESTTYPE, NULLVALUE, NULLSD, POWER, ...
                                     N, ALPHA)

  if (nargin != 6)
    error ("octave_calc_detectable: invalid number of input arguments.");
  endif
  [rows, errmsg] = octave_calc_sampsizepwr ('p1', TESTTYPE, NULLVALUE, ...
                                            NULLSD, [], POWER, N, ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_detectable: %s", errmsg);
  endif
  C = [{'Detectable difference', []}; cell(1, 2); rows];

endfunction

%!shared C
%! C = octave_calc_detectable ('t', 5, 2, 0.9, 30, 0.05);
%!test
%! assert_equal (C(1,1), {'Detectable difference'});
%!test
%! assert_equal (C(3,:), {'Test', 'one-sample or paired t-test'});
%!test
%! assert_equal (C(6,:), {'Power', 0.9});
%!test
%! assert_equal (C(end,:), ...
%!               {'Alternative value', sampsizepwr('t', [5 2], [], 0.9, 30)});
%!test
%! ## Nothing of the alternative is asked for, only what it would have to be
%! assert_equal (any (strcmp (C(:,1), 'Alternative value')), true);

%!error<octave_calc_detectable: invalid number of input arguments.> ...
%! octave_calc_detectable ('t', 5, 2, 0.9, 30)
%!error<octave_calc_detectable: TESTTYPE must be 'z', 't', 't2', 'var', 'p' or 'r'.> ...
%! octave_calc_detectable ('f', 5, 2, 0.9, 30, 0.05)
%!error<octave_calc_detectable: the power must be a number greater than 0 and less than 1.> ...
%! octave_calc_detectable ('t', 5, 2, 0, 30, 0.05)
%!error<octave_calc_detectable: the sample size must be a whole number of 2 or more.> ...
%! octave_calc_detectable ('t', 5, 2, 0.9, 0, 0.05)
%!error<octave_calc_detectable: the null value must be a number.> ...
%! octave_calc_detectable ('t', 'x', 2, 0.9, 30, 0.05)
