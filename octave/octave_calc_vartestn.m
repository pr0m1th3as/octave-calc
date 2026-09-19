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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_vartestn (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_vartestn (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_vartestn (@var{DATA}, @var{BY}, @var{NAMES}, @var{TESTTYPE})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_vartestn (@var{DATA}, @var{BY}, @var{NAMES}, @var{TESTTYPE}, @var{ALPHA})
##
## Test of equal variances for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_vartestn (@var{DATA}, @var{BY})} runs
## @code{vartestn} on the groups in @var{DATA}, ignoring @code{NaN}, which
## stands for an empty cell.  @var{BY} says how @var{DATA} holds the groups,
## @qcode{'columns'} or @qcode{'rows'}, one group each, or @qcode{'labels'},
## two columns holding each value beside the label of its group, and
## @var{NAMES} names the groups of the first two, as text, numbers, or empty
## to keep the name a group's place gives it.
##
## @var{TESTTYPE} is @qcode{'Bartlett'}, the default, @qcode{'LeveneQuadratic'},
## @qcode{'LeveneAbsolute'}, @qcode{'BrownForsythe'} or @qcode{'OBrien'}.
## Bartlett's test assumes each group is normal and returns a chi-square
## statistic; the rest run an ANOVA on deviations from the group's mean or
## median and return an F statistic with two degrees of freedom.  @var{ALPHA}
## is the significance level, 0.05 by default, and is named in the heading of
## the test.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; each group
## with its count, mean, variance and standard deviation; and the test with
## its statistic, degrees of freedom and p-value.  Where @var{DATA} holds
## exactly two groups, @code{vartest2} follows with the ratio of the first
## group's variance to the second's, its confidence interval and its own
## p-value, which no test of three or more groups can give.
##
## The @code{statistics} package must be loaded.
##
## @seealso{vartestn, vartest2}
## @end deftypefn

function C = octave_calc_vartestn (DATA, BY, NAMES, TESTTYPE, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 5)
    error ("octave_calc_vartestn: invalid number of input arguments.");
  endif
  if (nargin < 3)
    NAMES = [];
  endif
  if (nargin < 4)
    TESTTYPE = 'Bartlett';
  endif
  if (nargin < 5)
    ALPHA = 0.05;
  endif
  testtypes = {'Bartlett', 'LeveneQuadratic', 'LeveneAbsolute', ...
               'BrownForsythe', 'OBrien'};
  if (! (ischar (TESTTYPE) && any (strcmp (TESTTYPE, testtypes))))
    error (strcat ("octave_calc_vartestn: TESTTYPE must be 'Bartlett',", ...
                   " 'LeveneQuadratic', 'LeveneAbsolute',", ...
                   " 'BrownForsythe' or 'OBrien'."));
  endif
  errmsg = octave_calc_alpha (ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_vartestn: %s", errmsg);
  endif

  [x, group, labels, errmsg] = octave_calc_groups (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_vartestn: %s", errmsg);
  endif
  k = numel (labels);

  ## The test over every group, a row per figure so that the first column
  ## holds a name throughout, as every other block has it
  [p, stats] = vartestn (x, group, 'display', 'off', 'testtype', TESTTYPE);
  if (strcmp (TESTTYPE, 'Bartlett'))
    test = [pad('Statistic', stats.chisqstat); pad('DoF', stats.df); ...
            pad('p-value', p)];
  else
    test = [pad('Statistic', stats.fstat); ...
            pad('Numerator DoF', stats.df(1)); ...
            pad('Denominator DoF', stats.df(2)); pad('p-value', p)];
  endif

  ## The cells, eight columns wide
  counts = accumarray (group, 1);
  means = accumarray (group, x, [], @mean);
  variances = accumarray (group, x, [], @var);
  groups = [labels, num2cell(counts), num2cell(means), ...
            num2cell(variances), num2cell(sqrt (variances)), cell(k, 3)];
  C = [pad('Equal variances'); pad(); ...
       pad('Groups', 'Count', 'Mean', 'Variance', 'Standard deviation'); ...
       groups; pad(); ...
       pad(sprintf ("%s (alpha %g)", testname (TESTTYPE), ALPHA)); test];

  ## Two groups also have a ratio of variances, which no wider test gives
  if (k == 2)
    [~, p2, ci, stats2] = vartest2 (x(group == 1), x(group == 2), ...
                                    'alpha', ALPHA);
    C = [C; pad(); pad(sprintf ("Ratio of variances (alpha %g)", ALPHA)); ...
         pad('Group', 'Group', 'Lower bound', 'Variance ratio', ...
             'Upper bound', 'Numerator DoF', 'Denominator DoF', 'p-value'); ...
         pad(labels{1}, labels{2}, ci(1), stats2.fstat, ci(2), ...
             stats2.df1, stats2.df2, p2)];
  endif

endfunction

## How the heading names the test
function name = testname (TESTTYPE)
  switch (TESTTYPE)
    case 'Bartlett'
      name = "Bartlett's test";
    case 'LeveneQuadratic'
      name = "Levene's test on squared deviations";
    case 'LeveneAbsolute'
      name = "Levene's test on absolute deviations";
    case 'BrownForsythe'
      name = 'Brown-Forsythe test';
    case 'OBrien'
      name = "O'Brien's test";
  endswitch
endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, p, st
%! x = [1, 3, 2; 2, 5, 9; 4, 7, 3; 6, 9, 14; 8, 12, 5];
%! g = repmat ((1:3), 5, 1)(:);
%! [p, st] = vartestn (x(:), g, 'display', 'off');
%! C = octave_calc_vartestn (x, 'columns');
%!test
%! assert_equal (size (C), [11, 8]);
%!test
%! assert_equal (C(1,:), {'Equal variances', [], [], [], [], [], [], []});
%!test
%! assert_equal (C(3,:), {'Groups', 'Count', 'Mean', 'Variance', ...
%!                        'Standard deviation', [], [], []});
%!test
%! assert_equal (C(4,1:3), {'Column 1', 5, 4.2});
%!test
%! assert_equal (C(4,4:5), {var([1; 2; 4; 6; 8]), std([1; 2; 4; 6; 8])});
%!test
%! assert_equal (C(8,1), {"Bartlett's test (alpha 0.05)"});
%!test
%! assert_equal (C(9:11,1), {'Statistic'; 'DoF'; 'p-value'});
%!test
%! assert_equal (C(9:11,2), {st.chisqstat; st.df; p});

%!test
%! ## Three groups have no ratio of variances
%! C = octave_calc_vartestn ([1, 3, 2; 2, 5, 9; 4, 7, 3], 'columns');
%! assert_equal (rows (C), 11);

%!test
%! ## Two groups add the ratio, its interval and its own p-value
%! R = octave_calc_vartestn ([1, 3; 2, 5; 4, 7; 6, 9; 8, 12], 'columns');
%! assert_equal (rows (R), 14);
%!test
%! R = octave_calc_vartestn ([1, 3; 2, 5; 4, 7; 6, 9; 8, 12], 'columns');
%! assert_equal (R(12,1), {'Ratio of variances (alpha 0.05)'});
%!test
%! R = octave_calc_vartestn ([1, 3; 2, 5; 4, 7; 6, 9; 8, 12], 'columns');
%! assert_equal (R(13,:), {'Group', 'Group', 'Lower bound', ...
%!                         'Variance ratio', 'Upper bound', ...
%!                         'Numerator DoF', 'Denominator DoF', 'p-value'});
%!test
%! R = octave_calc_vartestn ([1, 3; 2, 5; 4, 7; 6, 9; 8, 12], 'columns');
%! a = [1; 2; 4; 6; 8];
%! b = [3; 5; 7; 9; 12];
%! [~, p2, ci, s2] = vartest2 (a, b);
%! assert_equal (R(14,3:8), {ci(1), s2.fstat, ci(2), s2.df1, s2.df2, p2});
%!test
%! R = octave_calc_vartestn ([1, 3; 2, 5; 4, 7; 6, 9; 8, 12], 'columns');
%! assert_equal (R{14,4}, var([1; 2; 4; 6; 8]) / var([3; 5; 7; 9; 12]));

%!test
%! ## Levene's test returns an F statistic with two degrees of freedom
%! R = octave_calc_vartestn ([1, 3, 2; 2, 5, 9; 4, 7, 3; 6, 9, 14], ...
%!                            'columns', [], 'LeveneAbsolute');
%! assert_equal (R(8,1), {"Levene's test on absolute deviations (alpha 0.05)"});
%!test
%! R = octave_calc_vartestn ([1, 3, 2; 2, 5, 9; 4, 7, 3; 6, 9, 14], ...
%!                            'columns', [], 'LeveneAbsolute');
%! assert_equal (R(9:12,1), {'Statistic'; 'Numerator DoF'; ...
%!                            'Denominator DoF'; 'p-value'});
%!test
%! R = octave_calc_vartestn ([1, 3, 2; 2, 5, 9; 4, 7, 3; 6, 9, 14], ...
%!                            'columns', [], 'BrownForsythe');
%! assert_equal (R(8,1), {'Brown-Forsythe test (alpha 0.05)'});
%!test
%! R = octave_calc_vartestn ([1, 3, 2; 2, 5, 9; 4, 7, 3; 6, 9, 14], ...
%!                            'columns', [], 'OBrien', 0.01);
%! assert_equal (R(8,1), {"O'Brien's test (alpha 0.01)"});

%!test
%! R = octave_calc_vartestn ([1, 2, 4, 6, 8; 3, 5, 7, 9, 12], 'rows');
%! assert_equal (R(4,1:2), {'Row 1', 5});

%!test
%! D = {1, 'a'; 3, 'b'; 2, 'a'; 5, 'b'};
%! R = octave_calc_vartestn (D, 'labels');
%! assert_equal (R(4:5,1:2), {'a', 2; 'b', 2});

%!error<octave_calc_vartestn: invalid number of input arguments.> ...
%! octave_calc_vartestn ([1, 2])
%!error<octave_calc_vartestn: TESTTYPE must be 'Bartlett', 'LeveneQuadratic', 'LeveneAbsolute', 'BrownForsythe' or 'OBrien'.> ...
%! octave_calc_vartestn ([1, 2; 3, 4], 'columns', [], 'Fligner')
%!error<octave_calc_vartestn: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_vartestn ([1, 2; 3, 4], 'columns', [], 'Bartlett', 0)
%!error<octave_calc_vartestn: BY must be 'columns', 'rows' or 'labels'.> ...
%! octave_calc_vartestn ([1, 2], 'diagonal')
%!error<octave_calc_vartestn: DATA must be a real numeric matrix.> ...
%! octave_calc_vartestn ('ab', 'columns')
%!error<octave_calc_vartestn: the input range holds fewer than two groups.> ...
%! octave_calc_vartestn ([1; 2], 'columns')
%!error<octave_calc_vartestn: the group 'Column 2' holds no numbers.> ...
%! octave_calc_vartestn ([1, NaN; 2, NaN], 'columns')
