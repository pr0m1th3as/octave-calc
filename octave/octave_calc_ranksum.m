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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_ranksum (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ranksum (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ranksum (@var{DATA}, @var{BY}, @var{NAMES}, @var{METHOD})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ranksum (@var{DATA}, @var{BY}, @var{NAMES}, @var{METHOD}, @var{TAIL})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ranksum (@var{DATA}, @var{BY}, @var{NAMES}, @var{METHOD}, @var{TAIL}, @var{ALPHA})
##
## Mann-Whitney U test for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_ranksum (@var{DATA}, @var{BY})} runs
## @code{ranksum} on the two groups in @var{DATA}, ignoring @code{NaN}, which
## stands for an empty cell.  @var{BY} says how @var{DATA} holds the groups,
## @qcode{'columns'} or @qcode{'rows'}, one group each, or @qcode{'labels'},
## two columns holding each value beside the label of its group, and
## @var{NAMES} names the groups of the first two, as text, numbers, or empty
## to keep the name a group's place gives it.  @var{DATA} must hold exactly
## two groups.
##
## @var{METHOD} is how the p-value is computed: @qcode{'auto'}, the default,
## which leaves the choice to @code{ranksum}, @qcode{'exact'}, or
## @qcode{'approximate'}.  @var{TAIL} is @qcode{'both'}, the default,
## @qcode{'right'}, which tests whether the first group's median is the
## greater, or @qcode{'left'}, whether it is the smaller.  @var{ALPHA} is the
## significance level, 0.05 by default.  The method actually used, the tail
## and the significance level are named in the heading of the test.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; each group
## with its count, median, mean rank, rank sum and interquartile range; and
## the two groups with the @var{U} statistic of the first, the z statistic,
## and the p-value.
##
## The ranks are of the two groups pooled, ties averaged, so that the rank
## sums add up to @code{N * (N + 1) / 2}.  @var{U} is the first group's rank
## sum less @code{n * (n + 1) / 2} for its own count.  The exact method
## computes no z statistic and reports @code{NaN} for it.
##
## The @code{statistics} package must be loaded.
##
## @seealso{ranksum}
## @end deftypefn

function C = octave_calc_ranksum (DATA, BY, NAMES, METHOD, TAIL, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 6)
    error ("octave_calc_ranksum: invalid number of input arguments.");
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
    error (strcat ("octave_calc_ranksum: METHOD must be 'auto', 'exact'", ...
                   " or 'approximate'."));
  endif
  [tail, errmsg] = octave_calc_tail (TAIL);
  if (! isempty (errmsg))
    error ("octave_calc_ranksum: %s", errmsg);
  endif
  errmsg = octave_calc_alpha (ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_ranksum: %s", errmsg);
  endif

  [x, group, labels, errmsg] = octave_calc_groups (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_ranksum: %s", errmsg);
  endif
  if (numel (labels) != 2)
    error (strcat ("octave_calc_ranksum: the input range must hold", ...
                   " exactly two groups."));
  endif

  ## The test, on the first group against the second
  args = {'tail', TAIL, 'alpha', ALPHA};
  if (! strcmp (METHOD, 'auto'))
    args = [args, {'method', METHOD}];
  endif
  [p, ~, stats] = ranksum (x(group == 1), x(group == 2), args{:});

  ## The ranks of the two groups pooled, and the first group's U from them
  ranks = tiedrank (x);
  counts = accumarray (group, 1);
  sums = accumarray (group, ranks);
  U = sums(1) - counts(1) * (counts(1) + 1) / 2;

  ## An exact p-value comes with no z statistic
  if (isempty (stats.zval))
    zval = NaN;
    method = 'exact';
  else
    zval = stats.zval;
    method = 'approximate';
  endif

  ## The cells, eight columns wide
  medians = accumarray (group, x, [], @median);
  spreads = accumarray (group, x, [], @iqr);
  heading = sprintf ("Ranks (%s, %s, alpha %g)", tail, method, ALPHA);
  groups = [labels, num2cell(counts), num2cell(medians), ...
            num2cell(sums ./ counts), num2cell(sums), num2cell(spreads), ...
            cell(2, 2)];
  C = [pad('Mann-Whitney U test'); pad(); ...
       pad('Groups', 'Count', 'Median', 'Mean rank', 'Rank sum', ...
           'Interquartile range'); groups; pad(); pad(heading); ...
       pad('Group', 'Group', 'U', 'z', 'p-value'); ...
       pad(labels{1}, labels{2}, U, zval, p)];

endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, p
%! x = [1, 3; 2, 5; 4, 7; 6, 9; 8, 11];
%! p = ranksum (x(:,1), x(:,2), 'tail', 'both', 'alpha', 0.05);
%! C = octave_calc_ranksum (x, 'columns');
%!test
%! assert_equal (size (C), [9, 8]);
%!test
%! assert_equal (C(1,:), {'Mann-Whitney U test', [], [], [], [], [], [], []});
%!test
%! assert_equal (C(3,:), {'Groups', 'Count', 'Median', 'Mean rank', ...
%!                        'Rank sum', 'Interquartile range', [], []});
%!test
%! assert_equal (C(4,1:3), {'Column 1', 5, 4});
%!test
%! assert_equal (C(5,1:3), {'Column 2', 5, 7});
%!test
%! ## The pooled ranks of ten values add up to 55
%! assert_equal (C{4,5} + C{5,5}, 55);
%!test
%! assert_equal (C(8,:), {'Group', 'Group', 'U', 'z', 'p-value', [], [], []});
%!test
%! assert_equal (C(9,1:2), {'Column 1', 'Column 2'});
%!test
%! assert_equal (C{9,3}, C{4,5} - 15);
%!test
%! assert_equal (C(9,5), {p});
%!test
%! ## A small sample is exact, so there is no z statistic
%! assert_equal (C{9,4}, NaN);
%!test
%! assert_equal (C(7,1), {'Ranks (two-sided, exact, alpha 0.05)'});

%!test
%! R = octave_calc_ranksum ([1, 2, 4, 6, 8; 3, 5, 7, 9, 11], 'rows');
%! assert_equal (R(4,1:3), {'Row 1', 5, 4});

%!test
%! R = octave_calc_ranksum ([1, 3; 2, 5; 4, 7; 6, 9; 8, 11], 'columns', ...
%!                           {'Treated', 'Control'});
%! assert_equal (R(9,1:2), {'Treated', 'Control'});

%!test
%! D = {1, 'a'; 3, 'b'; 2, 'a'; 5, 'b'};
%! R = octave_calc_ranksum (D, 'labels');
%! assert_equal (R(4:5,1:2), {'a', 2; 'b', 2});

%!test
%! ## The approximate method reports its z statistic and says so
%! R = octave_calc_ranksum ([1, 3; 2, 5; 4, 7; 6, 9; 8, 11], 'columns', [], ...
%!                           'approximate');
%! assert_equal (R(7,1), {'Ranks (two-sided, approximate, alpha 0.05)'});
%!test
%! R = octave_calc_ranksum ([1, 3; 2, 5; 4, 7; 6, 9; 8, 11], 'columns', [], ...
%!                           'approximate');
%! [~, ~, s] = ranksum ([1; 2; 4; 6; 8], [3; 5; 7; 9; 11], ...
%!                      'method', 'approximate');
%! assert_equal (R(9,4), {s.zval});

%!test
%! ## The rank sum of the smaller group is the one ranksum reports
%! D = [1, 3; 2, 5; 4, 7; 6, 9; NaN, 11];
%! R = octave_calc_ranksum (D, 'columns');
%! [~, ~, s] = ranksum ([1; 2; 4; 6], [3; 5; 7; 9; 11]);
%! assert_equal (R(4,5), {s.ranksum});

%!test
%! R = octave_calc_ranksum ([1, 3; 2, 5; 4, 7; 6, 9; 8, 11], 'columns', [], ...
%!                           'auto', 'left', 0.01);
%! assert_equal (R(7,1), {'Ranks (left-sided, exact, alpha 0.01)'});

%!error<octave_calc_ranksum: invalid number of input arguments.> ...
%! octave_calc_ranksum ([1, 2])
%!error<octave_calc_ranksum: METHOD must be 'auto', 'exact' or 'approximate'.> ...
%! octave_calc_ranksum ([1, 2; 3, 4], 'columns', [], 'network')
%!error<octave_calc_ranksum: TAIL must be 'both', 'right' or 'left'.> ...
%! octave_calc_ranksum ([1, 2; 3, 4], 'columns', [], 'auto', 'upper')
%!error<octave_calc_ranksum: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_ranksum ([1, 2; 3, 4], 'columns', [], 'auto', 'both', 1)
%!error<octave_calc_ranksum: BY must be 'columns', 'rows' or 'labels'.> ...
%! octave_calc_ranksum ([1, 2], 'diagonal')
%!error<octave_calc_ranksum: DATA must be a real numeric matrix.> ...
%! octave_calc_ranksum ('ab', 'columns')
%!error<octave_calc_ranksum: the input range holds fewer than two groups.> ...
%! octave_calc_ranksum ([1; 2], 'columns')
%!error<octave_calc_ranksum: the input range must hold exactly two groups.> ...
%! octave_calc_ranksum ([1, 2, 3; 4, 5, 6], 'columns')
%!error<octave_calc_ranksum: the group 'Column 2' holds no numbers.> ...
%! octave_calc_ranksum ([1, NaN; 2, NaN], 'columns')
