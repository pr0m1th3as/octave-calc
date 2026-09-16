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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_anova1 (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_anova1 (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_anova1 (@var{DATA}, @var{BY}, @var{NAMES}, @var{CTYPE})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_anova1 (@var{DATA}, @var{BY}, @var{NAMES}, @var{CTYPE}, @var{ALPHA})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_anova1 (@var{DATA}, @var{BY}, @var{NAMES}, @var{CTYPE}, @var{ALPHA}, @var{VARTYPE})
##
## One-way ANOVA for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_anova1 (@var{DATA}, @var{BY})} runs
## @code{anova1} on the groups in @var{DATA}, ignoring @code{NaN}, which
## stands for an empty cell.  The test is followed by the pairwise comparisons
## of the group means from @code{multcompare}.  @var{BY} says how @var{DATA}
## holds the groups, @qcode{'columns'} or @qcode{'rows'}, one group each, or
## @qcode{'labels'}, two columns holding each value beside the label of its
## group, and @var{NAMES} names the groups of the first two, as text, numbers,
## or empty to keep the name a group's place gives it.
##
## @var{CTYPE} is how the p-values of the comparisons are adjusted,
## @qcode{'holm'} by default, and @var{ALPHA} the significance level, 0.05 by
## default; both are named in the heading of the comparisons.  @var{VARTYPE}
## is @qcode{'equal'}, the default, which assumes the groups share a variance,
## or @qcode{'unequal'}, which runs Welch's ANOVA instead, returns its own
## table, and titles the results @qcode{"One-way Welch's ANOVA"}.
##
## @var{C} is a cell array of scalars, text and empty values, six columns wide,
## laid out as the cells written into the sheet: the title; each group with its
## count, mean and standard deviation; the table returned by @code{anova1}; and
## each pair of groups with the lower bound, estimate and upper bound of the
## difference of their means and its adjusted p-value.
##
## The @code{statistics} package must be loaded.
##
## @seealso{anova1, multcompare}
## @end deftypefn

function C = octave_calc_anova1 (DATA, BY, NAMES, CTYPE, ALPHA, VARTYPE)

  ## Input validation
  if (nargin < 2 || nargin > 6)
    error ("octave_calc_anova1: invalid number of input arguments.");
  endif
  if (nargin < 3)
    NAMES = [];
  endif
  if (nargin < 4)
    CTYPE = 'holm';
  endif
  if (nargin < 5)
    ALPHA = 0.05;
  endif
  if (nargin < 6)
    VARTYPE = 'equal';
  endif
  if (! (ischar (VARTYPE) && any (strcmp (VARTYPE, {'equal', 'unequal'}))))
    error (strcat ("octave_calc_anova1: VARTYPE must be 'equal' or", ...
                   " 'unequal'."));
  endif

  [x, group, labels, errmsg] = octave_calc_groups (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_anova1: %s", errmsg);
  endif
  k = numel (labels);

  ## The test, and the pairwise comparisons of its means
  [~, tbl, stats] = anova1 (x, group, 'off', VARTYPE);
  [heading, pairs, errmsg] = octave_calc_pairs (stats, labels, CTYPE, ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_anova1: %s", errmsg);
  endif

  ## The cells, six columns wide
  if (strcmp (VARTYPE, 'unequal'))
    title = "One-way Welch's ANOVA";
  else
    title = 'One-way ANOVA';
  endif
  groups = [labels, num2cell(stats.n(:)), num2cell(stats.means(:)), ...
            num2cell(sqrt (stats.vars(:))), cell(k, 2)];
  C = [pad(title); pad(); ...
       pad('Groups', 'Count', 'Mean', 'Standard deviation'); groups; pad(); ...
       tbl; pad(); pad(heading); ...
       pad('Group', 'Group', 'Lower bound', 'Mean difference', ...
           'Upper bound', 'Adjusted p-value'); pairs];

endfunction

## A row of six cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 6);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, tbl, c
%! x = [1, 4, 7; 2, 5, 9; 3, 6, 8];
%! [~, tbl, stats] = anova1 (x, [], 'off');
%! c = multcompare (stats, 'ctype', 'holm', 'alpha', 0.05, 'display', 'off');
%! C = octave_calc_anova1 (x, 'columns');
%!test
%! assert_equal (size (C), [17, 6]);
%!test
%! assert_equal (C(1,:), {'One-way ANOVA', [], [], [], [], []});
%!test
%! assert_equal (C(3,:), {'Groups', 'Count', 'Mean', 'Standard deviation', ...
%!                        [], []});
%!test
%! assert_equal (C(4,1:3), {'Column 1', 3, 2});
%!test
%! assert_equal (C(6,1:3), {'Column 3', 3, 8});
%!test
%! assert_equal (C(8:11,:), tbl);
%!test
%! assert_equal (C(13,1), {'Multiple comparisons (holm, alpha 0.05)'});
%!test
%! assert_equal (C(14,:), {'Group', 'Group', 'Lower bound', ...
%!                         'Mean difference', 'Upper bound', ...
%!                         'Adjusted p-value'});
%!test
%! assert_equal (C(15:17,3:6), num2cell (c(:,3:6)));
%!test
%! R = octave_calc_anova1 ([1, 2, 3; 4, 5, 6; 7, 8, 9], 'rows');
%! assert_equal (R(4,1:2), {'Row 1', 3});
%!test
%! R = octave_calc_anova1 ([1, 4, 7; 2, 5, 9; 3, 6, 8], 'columns', ...
%!                          {'A', 'B', 'C'});
%! assert_equal (R(4:6,1), {'A'; 'B'; 'C'});
%!test
%! D = {7, 'b'; 1, 'a'; 8, 'b'; 2, 'a'};
%! R = octave_calc_anova1 (D, 'labels');
%! assert_equal (R(4:5,1:3), {'b', 2, 7.5; 'a', 2, 1.5});
%!test
%! R = octave_calc_anova1 ([1, 4, 7; 2, 5, 9; 3, 6, 8], 'columns', [], ...
%!                          'bonferroni', 0.01);
%! assert_equal (R(13,1), {'Multiple comparisons (bonferroni, alpha 0.01)'});
%!test
%! ## Welch's ANOVA returns a table of its own, two rows deep
%! R = octave_calc_anova1 ([1, 4, 7; 2, 5, 9; 3, 6, 8], 'columns', [], ...
%!                          'holm', 0.05, 'unequal');
%! assert_equal (size (R), [15, 6]);
%!test
%! R = octave_calc_anova1 ([1, 4, 7; 2, 5, 9; 3, 6, 8], 'columns', [], ...
%!                          'holm', 0.05, 'unequal');
%! assert_equal (R(8,1:4), {'Source', 'F', 'df', 'dfe'});
%!test
%! R = octave_calc_anova1 ([1, 4, 7; 2, 5, 9; 3, 6, 8], 'columns', [], ...
%!                          'holm', 0.05, 'unequal');
%! assert_equal (R(1,1), {"One-way Welch's ANOVA"});

%!error<octave_calc_anova1: invalid number of input arguments.> ...
%! octave_calc_anova1 ([1, 2])
%!error<octave_calc_anova1: VARTYPE must be 'equal' or 'unequal'.> ...
%! octave_calc_anova1 ([1, 2; 3, 4], 'columns', [], 'holm', 0.05, 'other')
%!error<octave_calc_anova1: BY must be 'columns', 'rows' or 'labels'.> ...
%! octave_calc_anova1 ([1, 2], 'diagonal')
%!error<octave_calc_anova1: DATA must be a real numeric matrix.> ...
%! octave_calc_anova1 ('ab', 'columns')
%!error<octave_calc_anova1: the input range holds fewer than two groups.> ...
%! octave_calc_anova1 ([1; 2], 'columns')
%!error<octave_calc_anova1: the group 'Column 2' holds no numbers.> ...
%! octave_calc_anova1 ([1, NaN; 2, NaN], 'columns')
%!error<octave_calc_anova1: CTYPE must be 'bonferroni', 'scheffe', 'mvt', 'holm', 'hochberg', 'fdr' or 'lsd'.> ...
%! octave_calc_anova1 ([1, 2; 3, 4], 'columns', [], 'tukey')
%!error<octave_calc_anova1: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_anova1 ([1, 2; 3, 4], 'columns', [], 'holm', 1)
%!error<octave_calc_anova1: the input range holds a value with no group label.> ...
%! octave_calc_anova1 ({1, ''; 2, 'b'}, 'labels')
