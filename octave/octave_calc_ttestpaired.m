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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_ttestpaired (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ttestpaired (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ttestpaired (@var{DATA}, @var{BY}, @var{NAMES}, @var{TAIL})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ttestpaired (@var{DATA}, @var{BY}, @var{NAMES}, @var{TAIL}, @var{ALPHA})
##
## Paired t-test for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_ttestpaired (@var{DATA}, @var{BY})} runs
## @code{ttest} on the two measurements in @var{DATA}, taken on the same
## subjects.  @var{BY} says how @var{DATA} holds them, @qcode{'columns'}, one
## per column and a subject per row, or @qcode{'rows'}, one per row and a
## subject per column, and @var{NAMES} names them, as text, numbers, or empty
## to keep the name their place gives them.  @var{DATA} must hold exactly two
## measurements.  A subject missing either of them takes part in neither, and
## the results say how many were left out that way.
##
## @var{TAIL} is @qcode{'both'}, the default, @qcode{'right'}, which tests
## whether the first measurement is the greater, or @qcode{'left'}, whether it
## is the smaller.  @var{ALPHA} is the significance level, 0.05 by default;
## both are named in the heading of the test.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; each
## measurement and their difference with its count, mean, standard deviation
## and standard error; and the two measurements with the lower bound,
## estimate and upper bound of the mean difference, the test statistic, its
## degrees of freedom, and its p-value.
##
## The difference is the first measurement less the second.  A one-sided test
## bounds it on one side only, and the other bound is @code{Inf} or
## @code{-Inf}.
##
## The @code{statistics} package must be loaded.
##
## @seealso{ttest}
## @end deftypefn

function C = octave_calc_ttestpaired (DATA, BY, NAMES, TAIL, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 5)
    error ("octave_calc_ttestpaired: invalid number of input arguments.");
  endif
  if (nargin < 3)
    NAMES = [];
  endif
  if (nargin < 4)
    TAIL = 'both';
  endif
  if (nargin < 5)
    ALPHA = 0.05;
  endif
  [tail, errmsg] = octave_calc_tail (TAIL);
  if (! isempty (errmsg))
    error ("octave_calc_ttestpaired: %s", errmsg);
  endif
  errmsg = octave_calc_alpha (ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_ttestpaired: %s", errmsg);
  endif

  [X, labels, dropped, errmsg] = octave_calc_matched (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_ttestpaired: %s", errmsg);
  endif
  if (numel (labels) != 2)
    error (strcat ("octave_calc_ttestpaired: the input range must hold", ...
                   " exactly two measurements."));
  endif

  ## The test, on the first measurement against the second
  d = X(:,1) - X(:,2);
  [~, p, ci, stats] = ttest (X(:,1), X(:,2), 'tail', TAIL, 'alpha', ALPHA);

  ## The cells, eight columns wide
  n = rows (X);
  deviations = [std(X)(:); std(d)];
  means = [mean(X)(:); mean(d)];
  table = [[labels; 'Difference'], num2cell(repmat (n, 3, 1)), ...
           num2cell(means), num2cell(deviations), ...
           num2cell(deviations ./ sqrt (n)), cell(3, 3)];
  heading = sprintf ("Difference of means (%s, alpha %g)", tail, ALPHA);
  C = [pad('Paired t-test'); pad(); octave_calc_dropped(dropped); ...
       pad('Measurements', 'Count', 'Mean', 'Standard deviation', ...
           'Standard error'); table; pad(); pad(heading); ...
       pad('Measurement', 'Measurement', 'Lower bound', 'Mean difference', ...
           'Upper bound', 'Statistic', 'DoF', 'p-value'); ...
       pad(labels{1}, labels{2}, ci(1), mean (d), ci(2), stats.tstat, ...
           stats.df, p)];

endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, X, ci, st, p
%! X = [12, 14; 15, 18; 11, 13; 14, 15; 13, 16; 16, 17; 12, 15; 15, 19];
%! [~, p, ci, st] = ttest (X(:,1), X(:,2), 'tail', 'both', 'alpha', 0.05);
%! C = octave_calc_ttestpaired (X, 'columns');
%!test
%! assert_equal (size (C), [10, 8]);
%!test
%! assert_equal (C(1,:), {'Paired t-test', [], [], [], [], [], [], []});
%!test
%! assert_equal (C(3,:), {'Measurements', 'Count', 'Mean', ...
%!                        'Standard deviation', 'Standard error', [], [], []});
%!test
%! assert_equal (C(4,1:3), {'Column 1', 8, mean(X(:,1))});
%!test
%! assert_equal (C(5,1:3), {'Column 2', 8, mean(X(:,2))});
%!test
%! assert_equal (C(6,1:4), {'Difference', 8, mean(X(:,1) - X(:,2)), ...
%!                          std(X(:,1) - X(:,2))});
%!test
%! assert_equal (C(8,1), {'Difference of means (two-sided, alpha 0.05)'});
%!test
%! assert_equal (C(9,:), {'Measurement', 'Measurement', 'Lower bound', ...
%!                        'Mean difference', 'Upper bound', 'Statistic', ...
%!                        'DoF', 'p-value'});
%!test
%! assert_equal (C(10,3:8), {ci(1), mean(X(:,1) - X(:,2)), ci(2), ...
%!                           st.tstat, st.df, p});

%!test
%! ## The standard deviation of the difference is not that of either column
%! assert_equal (C{6,4}, st.sd);

%!test
%! R = octave_calc_ttestpaired (X.', 'rows');
%! assert_equal (R(4,1:3), {'Row 1', 8, mean(X(:,1))});

%!test
%! R = octave_calc_ttestpaired (X, 'columns', {'Before', 'After'});
%! assert_equal (R(10,1:2), {'Before', 'After'});

%!test
%! ## A subject missing a measurement takes part in neither
%! D = [X; 20, NaN];
%! R = octave_calc_ttestpaired (D, 'columns');
%! s = 'One subject was left out for a missing measurement.';
%! assert_equal (R(3,1), {s});
%!test
%! D = [X; 20, NaN];
%! R = octave_calc_ttestpaired (D, 'columns');
%! assert_equal (R(6,2), {8});
%!test
%! D = [X; 20, NaN; NaN, 21];
%! R = octave_calc_ttestpaired (D, 'columns');
%! s = '2 subjects were left out for a missing measurement.';
%! assert_equal (R(3,1), {s});
%!test
%! ## With none left out the sentence is absent
%! assert_equal (C(3,1), {'Measurements'});

%!test
%! ## A one-sided test leaves the other bound infinite
%! R = octave_calc_ttestpaired (X, 'columns', [], 'right');
%! assert_equal (R{10,5}, Inf);
%!test
%! R = octave_calc_ttestpaired (X, 'columns', [], 'left', 0.01);
%! assert_equal (R(8,1), {'Difference of means (left-sided, alpha 0.01)'});

%!error<octave_calc_ttestpaired: invalid number of input arguments.> ...
%! octave_calc_ttestpaired ([1, 2])
%!error<octave_calc_ttestpaired: TAIL must be 'both', 'right' or 'left'.> ...
%! octave_calc_ttestpaired ([1, 2; 3, 4], 'columns', [], 'upper')
%!error<octave_calc_ttestpaired: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_ttestpaired ([1, 2; 3, 4], 'columns', [], 'both', 1)
%!error<octave_calc_ttestpaired: BY must be 'columns' or 'rows'.> ...
%! octave_calc_ttestpaired ([1, 2], 'labels')
%!error<octave_calc_ttestpaired: DATA must be a real numeric matrix.> ...
%! octave_calc_ttestpaired ('ab', 'columns')
%!error<octave_calc_ttestpaired: the input range holds fewer than two measurements.> ...
%! octave_calc_ttestpaired ([1; 2], 'columns')
%!error<octave_calc_ttestpaired: the input range must hold exactly two measurements.> ...
%! octave_calc_ttestpaired ([1, 2, 3; 4, 5, 6], 'columns')
%!error<octave_calc_ttestpaired: two measurements share the name 'A'.> ...
%! octave_calc_ttestpaired ([1, 2; 3, 4], 'columns', {'A', 'A'})
%!error<octave_calc_ttestpaired: fewer than two subjects hold every measurement; there is nothing to compare.> ...
%! octave_calc_ttestpaired ([1, 2; 3, NaN], 'columns')
