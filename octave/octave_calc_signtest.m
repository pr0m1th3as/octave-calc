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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_signtest (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_signtest (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_signtest (@var{DATA}, @var{BY}, @var{NAMES}, @var{METHOD})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_signtest (@var{DATA}, @var{BY}, @var{NAMES}, @var{METHOD}, @var{TAIL})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_signtest (@var{DATA}, @var{BY}, @var{NAMES}, @var{METHOD}, @var{TAIL}, @var{ALPHA})
##
## Sign test for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_signtest (@var{DATA}, @var{BY})} runs
## @code{signtest} on the two measurements in @var{DATA}, taken on the same
## subjects.  @var{BY} says how @var{DATA} holds them, @qcode{'columns'}, one
## per column and a subject per row, or @qcode{'rows'}, one per row and a
## subject per column, and @var{NAMES} names them, as text, numbers, or empty
## to keep the name their place gives them.  @var{DATA} must hold exactly two
## measurements.  A subject missing either of them takes part in neither, and
## the results say how many were left out that way.
##
## @var{METHOD} is how the p-value is computed: @qcode{'auto'}, the default,
## which leaves the choice to @code{signtest}, @qcode{'exact'}, or
## @qcode{'approximate'}.  @var{TAIL} is @qcode{'both'}, the default,
## @qcode{'right'}, which tests whether the first measurement is the greater,
## or @qcode{'left'}, whether it is the smaller.  @var{ALPHA} is the
## significance level, 0.05 by default.  The method actually used, the tail
## and the significance level are named in the heading of the test.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; each
## measurement and their difference with its count, median and interquartile
## range; and the two measurements with the number of differences that are
## not zero, how many of those are positive, the z statistic, and the
## p-value.
##
## The difference is the first measurement less the second.  A subject whose
## two measurements are equal has no sign and takes no part in the test,
## which is why the count here may be smaller than the count above.  The
## exact method computes no z statistic and reports @code{NaN} for it.
##
## The @code{statistics} package must be loaded.
##
## @seealso{signtest}
## @end deftypefn

function C = octave_calc_signtest (DATA, BY, NAMES, METHOD, TAIL, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 6)
    error ("octave_calc_signtest: invalid number of input arguments.");
  endif
  if (nargin < 3)
    NAMES = [];
  endif
  if (nargin < 4)
    METHOD = 'auto';
  endif
  if (nargin < 5)
    TAIL = 'both';
  endif
  if (nargin < 6)
    ALPHA = 0.05;
  endif
  methods = {'auto', 'exact', 'approximate'};
  if (! (ischar (METHOD) && any (strcmp (METHOD, methods))))
    error (strcat ("octave_calc_signtest: METHOD must be 'auto',", ...
                   " 'exact' or 'approximate'."));
  endif
  [tail, errmsg] = octave_calc_tail (TAIL);
  if (! isempty (errmsg))
    error ("octave_calc_signtest: %s", errmsg);
  endif
  errmsg = octave_calc_alpha (ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_signtest: %s", errmsg);
  endif

  [X, labels, dropped, errmsg] = octave_calc_matched (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_signtest: %s", errmsg);
  endif
  if (numel (labels) != 2)
    error (strcat ("octave_calc_signtest: the input range must hold", ...
                   " exactly two measurements."));
  endif

  ## The test, on the first measurement against the second
  args = {'tail', TAIL, 'alpha', ALPHA};
  if (! strcmp (METHOD, 'auto'))
    args = [args, {'method', METHOD}];
  endif
  [p, ~, stats] = signtest (X(:,1), X(:,2), args{:});

  ## An exact p-value comes with no z statistic
  if (isnan (stats.zval))
    method = 'exact';
  else
    method = 'approximate';
  endif

  ## The cells, eight columns wide
  n = rows (X);
  d = X(:,1) - X(:,2);
  medians = [median(X)(:); median(d)];
  spreads = [iqr(X)(:); iqr(d)];
  table = [[labels; 'Difference'], num2cell(repmat (n, 3, 1)), ...
           num2cell(medians), num2cell(spreads), cell(3, 4)];
  heading = sprintf ("Signs (%s, %s, alpha %g)", tail, method, ALPHA);
  C = [pad('Sign test'); pad(); octave_calc_dropped(dropped); ...
       pad('Measurements', 'Count', 'Median', 'Interquartile range'); ...
       table; pad(); pad(heading); ...
       pad('Measurement', 'Measurement', 'Differences that are not zero', ...
           'Positive differences', 'z', 'p-value'); ...
       pad(labels{1}, labels{2}, sum (d != 0), stats.sign, stats.zval, p)];

endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, X, st, p
%! X = [12, 14; 15, 18; 11, 13; 14, 15; 13, 16; 16, 17; 12, 15; 15, 19];
%! [p, ~, st] = signtest (X(:,1), X(:,2), 'tail', 'both', 'alpha', 0.05);
%! C = octave_calc_signtest (X, 'columns');
%!test
%! assert_equal (size (C), [10, 8]);
%!test
%! assert_equal (C(1,1), {'Sign test'});
%!test
%! assert_equal (C(3,:), {'Measurements', 'Count', 'Median', ...
%!                        'Interquartile range', [], [], [], []});
%!test
%! assert_equal (C(4,1:3), {'Column 1', 8, median(X(:,1))});
%!test
%! assert_equal (C(6,1:3), {'Difference', 8, median(X(:,1) - X(:,2))});
%!test
%! assert_equal (C(8,1), {'Signs (two-sided, exact, alpha 0.05)'});
%!test
%! assert_equal (C(9,1:6), {'Measurement', 'Measurement', ...
%!                          'Differences that are not zero', ...
%!                          'Positive differences', 'z', 'p-value'});
%!test
%! assert_equal (C(10,3:4), {8, st.sign});
%!test
%! assert_equal (C(10,6), {p});
%!test
%! ## A small sample is exact, so there is no z statistic
%! assert_equal (C{10,5}, NaN);

%!test
%! ## A subject whose measurements are equal has no sign and is not counted
%! D = [X; 20, 20];
%! R = octave_calc_signtest (D, 'columns');
%! assert_equal (R(6,2), {9});
%!test
%! D = [X; 20, 20];
%! R = octave_calc_signtest (D, 'columns');
%! assert_equal (R(10,3), {8});

%!test
%! ## The approximate method reports its z statistic and says so
%! R = octave_calc_signtest (X, 'columns', [], 'approximate');
%! assert_equal (R(8,1), {'Signs (two-sided, approximate, alpha 0.05)'});
%!test
%! R = octave_calc_signtest (X, 'columns', [], 'approximate');
%! [~, ~, s] = signtest (X(:,1), X(:,2), 'method', 'approximate');
%! assert_equal (R(10,5), {s.zval});

%!test
%! R = octave_calc_signtest (X.', 'rows');
%! assert_equal (R(4,1:3), {'Row 1', 8, median(X(:,1))});

%!test
%! R = octave_calc_signtest (X, 'columns', {'Before', 'After'});
%! assert_equal (R(10,1:2), {'Before', 'After'});

%!test
%! D = [X; 20, NaN];
%! R = octave_calc_signtest (D, 'columns');
%! s = 'One subject was left out for a missing measurement.';
%! assert_equal (R(3,1), {s});

%!test
%! R = octave_calc_signtest (X, 'columns', [], 'auto', 'left', 0.01);
%! assert_equal (R(8,1), {'Signs (left-sided, exact, alpha 0.01)'});

%!error<octave_calc_signtest: invalid number of input arguments.> ...
%! octave_calc_signtest ([1, 2])
%!error<octave_calc_signtest: METHOD must be 'auto', 'exact' or 'approximate'.> ...
%! octave_calc_signtest ([1, 2; 3, 4], 'columns', [], 'network')
%!error<octave_calc_signtest: TAIL must be 'both', 'right' or 'left'.> ...
%! octave_calc_signtest ([1, 2; 3, 4], 'columns', [], 'auto', 'upper')
%!error<octave_calc_signtest: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_signtest ([1, 2; 3, 4], 'columns', [], 'auto', 'both', 1)
%!error<octave_calc_signtest: BY must be 'columns' or 'rows'.> ...
%! octave_calc_signtest ([1, 2], 'labels')
%!error<octave_calc_signtest: DATA must be a real numeric matrix.> ...
%! octave_calc_signtest ('ab', 'columns')
%!error<octave_calc_signtest: the input range holds fewer than two measurements.> ...
%! octave_calc_signtest ([1; 2], 'columns')
%!error<octave_calc_signtest: the input range must hold exactly two measurements.> ...
%! octave_calc_signtest ([1, 2, 3; 4, 5, 6], 'columns')
%!error<octave_calc_signtest: fewer than two subjects hold every measurement; there is nothing to compare.> ...
%! octave_calc_signtest ([1, 2; 3, NaN], 'columns')
