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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_ttest2 (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ttest2 (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ttest2 (@var{DATA}, @var{BY}, @var{NAMES}, @var{VARTYPE})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ttest2 (@var{DATA}, @var{BY}, @var{NAMES}, @var{VARTYPE}, @var{TAIL})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ttest2 (@var{DATA}, @var{BY}, @var{NAMES}, @var{VARTYPE}, @var{TAIL}, @var{ALPHA})
##
## Two-sample t-test for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_ttest2 (@var{DATA}, @var{BY})} runs
## @code{ttest2} on the two groups in @var{DATA}, ignoring @code{NaN}, which
## stands for an empty cell.  @var{BY} says how @var{DATA} holds the groups,
## @qcode{'columns'} or @qcode{'rows'}, one group each, or @qcode{'labels'},
## two columns holding each value beside the label of its group, and
## @var{NAMES} names the groups of the first two, as text, numbers, or empty
## to keep the name a group's place gives it.  @var{DATA} must hold exactly
## two groups.
##
## @var{VARTYPE} is @qcode{'equal'}, the default, which assumes the groups
## share a variance, or @qcode{'unequal'}, which runs Welch's test instead and
## titles the results @qcode{"Welch's two-sample t-test"}.  @var{TAIL} is
## @qcode{'both'}, the default, @qcode{'right'}, which tests whether the first
## group's mean is the greater, or @qcode{'left'}, whether it is the smaller.
## @var{ALPHA} is the significance level, 0.05 by default; all three are named
## in the heading of the test.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; each group
## with its count, mean, standard deviation and standard error; and the two
## groups with the lower bound, estimate and upper bound of the difference of
## their means, the test statistic, its degrees of freedom, and its p-value.
##
## The difference is the first group's mean less the second group's.  A
## one-sided test bounds it on one side only, and the other bound is
## @code{Inf} or @code{-Inf}.
##
## The @code{statistics} package must be loaded.
##
## @seealso{ttest2}
## @end deftypefn

function C = octave_calc_ttest2 (DATA, BY, NAMES, VARTYPE, TAIL, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 6)
    error ("octave_calc_ttest2: invalid number of input arguments.");
  endif
  if (nargin < 3)
    NAMES = [];
  endif
  if (nargin < 4)
    VARTYPE = 'equal';
  endif
  if (nargin < 5)
    TAIL = 'both';
  endif
  if (nargin < 6)
    ALPHA = 0.05;
  endif
  if (! (ischar (VARTYPE) && any (strcmp (VARTYPE, {'equal', 'unequal'}))))
    error (strcat ("octave_calc_ttest2: VARTYPE must be 'equal' or", ...
                   " 'unequal'."));
  endif
  [tail, errmsg] = octave_calc_tail (TAIL);
  if (! isempty (errmsg))
    error ("octave_calc_ttest2: %s", errmsg);
  endif
  errmsg = octave_calc_alpha (ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_ttest2: %s", errmsg);
  endif

  [x, group, labels, errmsg] = octave_calc_groups (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_ttest2: %s", errmsg);
  endif
  if (numel (labels) != 2)
    error (strcat ("octave_calc_ttest2: the input range must hold", ...
                   " exactly two groups."));
  endif

  ## The test, on the first group against the second
  [~, p, ci, stats] = ttest2 (x(group == 1), x(group == 2), ...
                              'vartype', VARTYPE, 'tail', TAIL, ...
                              'alpha', ALPHA);
  counts = accumarray (group, 1);
  means = accumarray (group, x, [], @mean);
  deviations = accumarray (group, x, [], @std);

  ## The cells, eight columns wide
  if (strcmp (VARTYPE, 'unequal'))
    title = "Welch's two-sample t-test";
  else
    title = 'Two-sample t-test';
  endif
  heading = sprintf ("Difference of means (%s, %s variances, alpha %g)", ...
                     tail, VARTYPE, ALPHA);
  groups = [labels, num2cell(counts), num2cell(means), ...
            num2cell(deviations), num2cell(deviations ./ sqrt (counts)), ...
            cell(2, 3)];
  C = [pad(title); pad(); ...
       pad('Groups', 'Count', 'Mean', 'Standard deviation', ...
           'Standard error'); groups; pad(); pad(heading); ...
       pad('Group', 'Group', 'Lower bound', 'Mean difference', ...
           'Upper bound', 'Statistic', 'DoF', 'p-value'); ...
       pad(labels{1}, labels{2}, ci(1), means(1) - means(2), ci(2), ...
           stats.tstat, stats.df, p)];

endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, ci, st, p
%! x = [1, 3; 2, 5; 3, 7; 4, 9; 5, 11];
%! [~, p, ci, st] = ttest2 (x(:,1), x(:,2), 'vartype', 'equal', ...
%!                          'tail', 'both', 'alpha', 0.05);
%! C = octave_calc_ttest2 (x, 'columns');
%!test
%! assert_equal (size (C), [9, 8]);
%!test
%! assert_equal (C(1,:), {'Two-sample t-test', [], [], [], [], [], [], []});
%!test
%! assert_equal (C(3,:), {'Groups', 'Count', 'Mean', 'Standard deviation', ...
%!                        'Standard error', [], [], []});
%!test
%! assert_equal (C(4,1:3), {'Column 1', 5, 3});
%!test
%! assert_equal (C(5,1:3), {'Column 2', 5, 7});
%!test
%! s = std ([1; 2; 3; 4; 5]);
%! assert_equal (C(4,4:5), {s, s / sqrt(5)});
%!test
%! s = 'Difference of means (two-sided, equal variances, alpha 0.05)';
%! assert_equal (C(7,1), {s});
%!test
%! assert_equal (C(8,:), {'Group', 'Group', 'Lower bound', ...
%!                        'Mean difference', 'Upper bound', 'Statistic', ...
%!                        'DoF', 'p-value'});
%!test
%! assert_equal (C(9,1:2), {'Column 1', 'Column 2'});
%!test
%! assert_equal (C(9,3:8), {ci(1), -4, ci(2), st.tstat, st.df, p});

%!test
%! R = octave_calc_ttest2 ([1, 2, 3, 4, 5; 3, 5, 7, 9, 11], 'rows');
%! assert_equal (R(4,1:3), {'Row 1', 5, 3});

%!test
%! R = octave_calc_ttest2 ([1, 3; 2, 5; 3, 7; 4, 9; 5, 11], 'columns', ...
%!                          {'Before', 'After'});
%! assert_equal (R(9,1:2), {'Before', 'After'});

%!test
%! D = {1, 'a'; 3, 'b'; 2, 'a'; 5, 'b'};
%! R = octave_calc_ttest2 (D, 'labels');
%! assert_equal (R(4:5,1:2), {'a', 2; 'b', 2});

%!test
%! ## Welch's test carries its own title and fractional degrees of freedom
%! R = octave_calc_ttest2 ([1, 3; 2, 5; 3, 7; 4, 9; 5, 11], 'columns', [], ...
%!                          'unequal');
%! assert_equal (R(1,1), {"Welch's two-sample t-test"});
%!test
%! R = octave_calc_ttest2 ([1, 3; 2, 5; 3, 7; 4, 9; 5, 11], 'columns', [], ...
%!                          'unequal');
%! [~, ~, ~, s] = ttest2 ([1; 2; 3; 4; 5], [3; 5; 7; 9; 11], ...
%!                        'vartype', 'unequal');
%! assert_equal (R(9,7), {s.df});

%!test
%! ## A one-sided test leaves the other bound infinite
%! R = octave_calc_ttest2 ([1, 3; 2, 5; 3, 7; 4, 9; 5, 11], 'columns', [], ...
%!                          'equal', 'right');
%! assert_equal (R{9,5}, Inf);
%!test
%! R = octave_calc_ttest2 ([1, 3; 2, 5; 3, 7; 4, 9; 5, 11], 'columns', [], ...
%!                          'equal', 'left');
%! assert_equal (R{9,3}, -Inf);
%!test
%! R = octave_calc_ttest2 ([1, 3; 2, 5; 3, 7; 4, 9; 5, 11], 'columns', [], ...
%!                          'equal', 'left', 0.01);
%! s = 'Difference of means (left-sided, equal variances, alpha 0.01)';
%! assert_equal (R(7,1), {s});

%!error<octave_calc_ttest2: invalid number of input arguments.> ...
%! octave_calc_ttest2 ([1, 2])
%!error<octave_calc_ttest2: VARTYPE must be 'equal' or 'unequal'.> ...
%! octave_calc_ttest2 ([1, 2; 3, 4], 'columns', [], 'other')
%!error<octave_calc_ttest2: TAIL must be 'both', 'right' or 'left'.> ...
%! octave_calc_ttest2 ([1, 2; 3, 4], 'columns', [], 'equal', 'upper')
%!error<octave_calc_ttest2: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_ttest2 ([1, 2; 3, 4], 'columns', [], 'equal', 'both', 1)
%!error<octave_calc_ttest2: BY must be 'columns', 'rows' or 'labels'.> ...
%! octave_calc_ttest2 ([1, 2], 'diagonal')
%!error<octave_calc_ttest2: DATA must be a real numeric matrix.> ...
%! octave_calc_ttest2 ('ab', 'columns')
%!error<octave_calc_ttest2: the input range holds fewer than two groups.> ...
%! octave_calc_ttest2 ([1; 2], 'columns')
%!error<octave_calc_ttest2: the input range must hold exactly two groups.> ...
%! octave_calc_ttest2 ([1, 2, 3; 4, 5, 6], 'columns')
%!error<octave_calc_ttest2: the group 'Column 2' holds no numbers.> ...
%! octave_calc_ttest2 ([1, NaN; 2, NaN], 'columns')
