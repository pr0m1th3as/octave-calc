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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_kruskalwallis (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_kruskalwallis (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_kruskalwallis (@var{DATA}, @var{BY}, @var{NAMES}, @var{CTYPE})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_kruskalwallis (@var{DATA}, @var{BY}, @var{NAMES}, @var{CTYPE}, @var{ALPHA})
##
## Kruskal-Wallis Test for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_kruskalwallis (@var{DATA}, @var{BY})} runs
## @code{kruskalwallis} on the groups in @var{DATA}, ignoring @code{NaN}, which
## stands for an empty cell.  The test is followed by the pairwise comparisons
## of the mean ranks from @code{multcompare}, with Holm's adjustment of the
## p-values.  @var{BY} says how @var{DATA} holds the groups:
##
## @itemize
## @item @qcode{'columns'}: a numeric matrix with one group per column, named
## @qcode{'Column 1'}, @qcode{'Column 2'} and so on.
## @item @qcode{'rows'}: a numeric matrix with one group per row, named
## @qcode{'Row 1'} and so on.
## @item @qcode{'labels'}: two columns, each value beside the label of its
## group, either a numeric matrix or a cell array holding numbers and empty
## values in its first column and text, numbers and empty values in its
## second.  A group is named after its label.  Numeric labels are ordered from
## the smallest; when any label is text, the groups are ordered as they first
## appear.  A row without a value is ignored, and a value without a label is
## an error.
## @end itemize
##
## @code{@var{C} = octave_calc_kruskalwallis (@var{DATA}, @var{BY},
## @var{NAMES})} names the groups in columns or rows after @var{NAMES}, a
## vector with one name per group, as text, a number, or empty to keep the
## name the group's place gives it.  An empty @var{NAMES} names nothing, and
## is the only one @qcode{'labels'} accepts.
##
## @var{CTYPE} is how @code{multcompare} adjusts the p-values of the pairwise
## comparisons, one of @qcode{'bonferroni'}, @qcode{'scheffe'},
## @qcode{'mvt'}, @qcode{'holm'} (the default), @qcode{'hochberg'},
## @qcode{'fdr'} or @qcode{'lsd'}, and @var{ALPHA} is the significance level,
## greater than 0 and less than 1, 0.05 by default, which also sets the
## confidence intervals of the comparisons.  Both are named in the heading of
## the comparisons.
##
## @var{C} is a cell array of scalars, text and empty values, six columns wide,
## laid out as the cells written into the sheet: the title; each group with its
## count, median and mean rank; the table returned by @code{kruskalwallis}; and
## each pair of groups with the lower bound, estimate and upper bound of their
## difference in mean ranks and its adjusted p-value.
##
## The @code{statistics} package must be loaded.
##
## @seealso{kruskalwallis, multcompare}
## @end deftypefn

function C = octave_calc_kruskalwallis (DATA, BY, NAMES, CTYPE, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 5)
    error ("octave_calc_kruskalwallis: invalid number of input arguments.");
  endif
  if (nargin < 4)
    CTYPE = 'holm';
  endif
  if (nargin < 5)
    ALPHA = 0.05;
  endif

  if (nargin < 3)
    NAMES = [];
  endif

  [x, group, labels, errmsg] = octave_calc_groups (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_kruskalwallis: %s", errmsg);
  endif
  k = numel (labels);

  ## The test, and the pairwise comparisons of its mean ranks
  [~, tbl, stats] = kruskalwallis (x, group, 'off');
  [heading, pairs, errmsg] = octave_calc_pairs (stats, labels, CTYPE, ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_kruskalwallis: %s", errmsg);
  endif
  medians = accumarray (group, x, [], @median);

  ## The cells, six columns wide
  groups = [labels, num2cell(stats.n(:)), num2cell(medians), ...
            num2cell(stats.meanranks(:)), cell(k, 2)];
  C = [pad('Kruskal-Wallis Test'); pad(); ...
       pad('Groups', 'Count', 'Median', 'Mean rank'); groups; pad(); ...
       tbl; pad(); pad(heading); ...
       pad('Group', 'Group', 'Lower bound', 'Mean rank difference', ...
           'Upper bound', 'Adjusted p-value'); pairs];

endfunction

## A row of six cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 6);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, tbl, c
%! x = (1:9)';
%! g = [1; 1; 1; 2; 2; 2; 3; 3; 3];
%! [~, tbl, stats] = kruskalwallis (x, g, 'off');
%! c = multcompare (stats, 'ctype', 'holm', 'display', 'off');
%! C = octave_calc_kruskalwallis ([1, 4, 7; 2, 5, 8; 3, 6, 9], 'columns');
%!test
%! assert_equal (size (C), [17, 6]);
%!test
%! assert_equal (C(1,:), {'Kruskal-Wallis Test', [], [], [], [], []});
%!test
%! assert_equal (C(3,:), {'Groups', 'Count', 'Median', 'Mean rank', [], []});
%!test
%! assert_equal (C(4,:), {'Column 1', 3, 2, 2, [], []});
%!test
%! assert_equal (C(6,:), {'Column 3', 3, 8, 8, [], []});
%!test
%! assert_equal (C(8:11,:), tbl);
%!test
%! assert_equal (C(13,1), {'Multiple comparisons (holm, alpha 0.05)'});
%!test
%! R = octave_calc_kruskalwallis ([1, 4, 7; 2, 5, 8; 3, 6, 9], 'columns', ...
%!                                [], 'bonferroni', 0.01);
%! assert_equal (R(13,1), {'Multiple comparisons (bonferroni, alpha 0.01)'});
%!test
%! R = octave_calc_kruskalwallis ([1, 4, 7; 2, 5, 8; 3, 6, 9], 'columns', ...
%!                                [], 'lsd');
%! assert_equal (isequal (R(15:17,6), C(15:17,6)), false);
%!test
%! R = octave_calc_kruskalwallis ([1, 4, 7; 2, 5, 8; 3, 6, 9], 'columns', ...
%!                                [], 'holm', 0.5);
%! assert_equal (isequal (R(15:17,3), C(15:17,3)), false);
%!test
%! assert_equal (C(14,:), {'Group', 'Group', 'Lower bound', ...
%!                         'Mean rank difference', 'Upper bound', ...
%!                         'Adjusted p-value'});
%!test
%! assert_equal (C(15:17,1:2), {'Column 1', 'Column 2'; 'Column 1', ...
%!                              'Column 3'; 'Column 2', 'Column 3'});
%!test
%! assert_equal (C(15:17,3:6), num2cell (c(:,3:6)));
%!test
%! R = octave_calc_kruskalwallis ([1, 2, 3; 4, 5, 6; 7, 8, 9], 'rows');
%! assert_equal (R(4,:), {'Row 1', 3, 2, 2, [], []});
%!test
%! R = octave_calc_kruskalwallis ([1, 4; 2, NaN; 3, 6], 'columns');
%! assert_equal (R(5,1:4), {'Column 2', 2, 5, 4.5});
%!test
%! R = octave_calc_kruskalwallis ([1, 4, 7; 2, 5, 8; 3, 6, 9], 'columns', ...
%!                                {'A', '', 2020});
%! assert_equal (R(4:6,1), {'A'; 'Column 2'; '2020'});
%!test
%! R = octave_calc_kruskalwallis ([1, 2, 3; 4, 5, 6; 7, 8, 9], 'rows', ...
%!                                {'A'; 'B'; ''});
%! assert_equal (R(4:6,1), {'A'; 'B'; 'Row 3'});
%!test
%! R = octave_calc_kruskalwallis ([1, 4, 7; 2, 5, 8; 3, 6, 9], 'columns', []);
%! assert_equal (R(4,1), {'Column 1'});
%!test
%! R = octave_calc_kruskalwallis ([1, 1; NaN, 2; 3, 2; 4, 1], 'labels', []);
%! assert_equal (R(4:5,1:2), {'1', 2; '2', 1});
%!test
%! R = octave_calc_kruskalwallis ([1, 4, 7, 2, 5, 8, 3, 6, 9; ...
%!                                 10, 20, 30, 10, 20, 30, 10, 20, 30]', ...
%!                                'labels');
%! assert_equal (R(8:11,:), tbl);
%!test
%! R = octave_calc_kruskalwallis ([4, 2.5; 1, 1; 7, 30; 2, 1], 'labels');
%! assert_equal (R(4:6,1:2), {'1', 2; '2.5', 1; '30', 1});
%!test
%! D = {7, 'b'; 1, 'a'; 8, 'b'; 2, 'a'};
%! R = octave_calc_kruskalwallis (D, 'labels');
%! assert_equal (R(4:5,1:3), {'b', 2, 7.5; 'a', 2, 1.5});
%!test
%! D = {7, 'b'; 1, 2; 8, 'b'; 2, 2};
%! R = octave_calc_kruskalwallis (D, 'labels');
%! assert_equal (R(4:5,1:2), {'b', 2; '2', 2});
%!test
%! D = {7, 'b'; [], ''; 1, 'a'; [], 'c'; 8, 'b'; 2, 'a'};
%! R = octave_calc_kruskalwallis (D, 'labels');
%! assert_equal (R(4:6,1:2), {'b', 2; 'a', 2; [], []});
%!test
%! R = octave_calc_kruskalwallis ([1, 1; NaN, 2; 3, 2; 4, 1], 'labels');
%! assert_equal (R(4:5,1:2), {'1', 2; '2', 1});

%!error<octave_calc_kruskalwallis: invalid number of input arguments.> ...
%! octave_calc_kruskalwallis ([1, 2])
%!error<octave_calc_kruskalwallis: BY must be 'columns', 'rows' or 'labels'.> ...
%! octave_calc_kruskalwallis ([1, 2], 'diagonal')
%!error<octave_calc_kruskalwallis: NAMES applies only to groups in columns or rows.> ...
%! octave_calc_kruskalwallis ([1, 1; 2, 2], 'labels', {'A', 'B'})
%!error<octave_calc_kruskalwallis: CTYPE must be 'bonferroni', 'scheffe', 'mvt', 'holm', 'hochberg', 'fdr' or 'lsd'.> ...
%! octave_calc_kruskalwallis ([1, 2; 3, 4], 'columns', [], 'tukey')
%!error<octave_calc_kruskalwallis: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_kruskalwallis ([1, 2; 3, 4], 'columns', [], 'holm', 1)
%!error<octave_calc_kruskalwallis: DATA must be a real numeric matrix.> ...
%! octave_calc_kruskalwallis ('ab', 'columns')
%!error<octave_calc_kruskalwallis: NAMES must be text or numbers.> ...
%! octave_calc_kruskalwallis ([1, 2; 3, 4], 'columns', {{'A'}, 'B'})
%!error<octave_calc_kruskalwallis: NAMES must hold one name for each group.> ...
%! octave_calc_kruskalwallis ([1, 2; 3, 4], 'columns', {'A'})
%!error<octave_calc_kruskalwallis: two groups share the name 'A'.> ...
%! octave_calc_kruskalwallis ([1, 2; 3, 4], 'columns', {'A', 'A'})
%!error<octave_calc_kruskalwallis: the input range holds fewer than two groups.> ...
%! octave_calc_kruskalwallis ([1; 2], 'columns')
%!error<octave_calc_kruskalwallis: the group 'Column 2' holds no numbers.> ...
%! octave_calc_kruskalwallis ([1, NaN; 2, NaN], 'columns')
%!error<octave_calc_kruskalwallis: DATA must have two columns, the values and their group labels.> ...
%! octave_calc_kruskalwallis ([1, 2, 3], 'labels')
%!error<octave_calc_kruskalwallis: the values in DATA must be numbers.> ...
%! octave_calc_kruskalwallis ({'x', 'a'; 1, 'b'}, 'labels')
%!error<octave_calc_kruskalwallis: the group labels in DATA must be text or numbers.> ...
%! octave_calc_kruskalwallis ({1, {'a'}; 2, 'b'}, 'labels')
%!error<octave_calc_kruskalwallis: the input range holds a value with no group label.> ...
%! octave_calc_kruskalwallis ({1, ''; 2, 'b'}, 'labels')
%!error<octave_calc_kruskalwallis: the input range holds a value with no group label.> ...
%! octave_calc_kruskalwallis ([1, NaN; 2, 1], 'labels')
%!error<octave_calc_kruskalwallis: the input range holds fewer than two groups.> ...
%! octave_calc_kruskalwallis ([1, 1; 2, 1], 'labels')
