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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_friedman (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_friedman (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_friedman (@var{DATA}, @var{BY}, @var{NAMES}, @var{CTYPE})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_friedman (@var{DATA}, @var{BY}, @var{NAMES}, @var{CTYPE}, @var{ALPHA})
##
## Friedman test for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_friedman (@var{DATA}, @var{BY})} runs
## @code{friedman} on the measurements in @var{DATA}, taken on the same
## subjects, ranking them within each subject.  @var{BY} says how @var{DATA}
## holds them, @qcode{'columns'}, one per column and a subject per row, or
## @qcode{'rows'}, one per row and a subject per column, and @var{NAMES} names
## them, as text, numbers, or empty to keep the name their place gives them.
## A subject missing any measurement takes part in none of them, and the
## results say how many were left out that way.
##
## The test is followed by the pairwise comparisons of the mean ranks from
## @code{multcompare}.  @var{CTYPE} is how their p-values are adjusted,
## @qcode{'holm'} by default, and @var{ALPHA} the significance level, 0.05 by
## default; both are named in the heading of the comparisons.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; each
## measurement with its count, median, mean rank and interquartile range; the
## table returned by @code{friedman}; and each pair of measurements with the
## lower bound, estimate and upper bound of the difference of their mean
## ranks, the test statistic, its degrees of freedom, and its adjusted
## p-value.
##
## The ranks are within a subject, so each subject ranks the measurements
## from 1 to however many there are, and the mean rank is over the subjects.
##
## The @code{statistics} package must be loaded.
##
## @seealso{friedman, multcompare}
## @end deftypefn

function C = octave_calc_friedman (DATA, BY, NAMES, CTYPE, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 5)
    error ("octave_calc_friedman: invalid number of input arguments.");
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

  [X, labels, dropped, errmsg] = octave_calc_matched (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_friedman: %s", errmsg);
  endif
  k = numel (labels);

  ## The test, and the pairwise comparisons of its mean ranks
  [~, tbl, stats] = friedman (X, 1, 'off');
  [heading, pairs, errmsg] = octave_calc_pairs (stats, labels, CTYPE, ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_friedman: %s", errmsg);
  endif

  ## The cells, eight columns wide
  n = rows (X);
  table = [labels, num2cell(repmat (n, k, 1)), num2cell(median(X)(:)), ...
           num2cell(stats.meanranks(:)), num2cell(iqr(X)(:)), cell(k, 3)];
  C = [pad('Friedman test'); pad(); octave_calc_dropped(dropped); ...
       pad('Measurements', 'Count', 'Median', 'Mean rank', ...
           'Interquartile range'); table; pad(); ...
       [octave_calc_dof(tbl), cell(rows (tbl), 2)]; pad(); pad(heading); ...
       pad('Measurement', 'Measurement', 'Lower bound', ...
           'Mean rank difference', 'Upper bound', 'Statistic', 'DoF', ...
           'Adjusted p-value'); pairs];

endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, X, tbl, st, c
%! X = [12, 14, 13; 15, 18, 16; 11, 13, 12; 14, 15, 13; ...
%!      13, 16, 15; 16, 17, 18; 12, 15, 14; 15, 19, 17];
%! [~, tbl, st] = friedman (X, 1, 'off');
%! c = multcompare (st, 'ctype', 'holm', 'alpha', 0.05, 'display', 'off');
%! C = octave_calc_friedman (X, 'columns');
%!test
%! assert_equal (size (C), [17, 8]);
%!test
%! assert_equal (C(1,1), {'Friedman test'});
%!test
%! assert_equal (C(3,:), {'Measurements', 'Count', 'Median', 'Mean rank', ...
%!                        'Interquartile range', [], [], []});
%!test
%! assert_equal (C(4,1:4), {'Column 1', 8, median(X(:,1)), st.meanranks(1)});
%!test
%! assert_equal (C(6,1:4), {'Column 3', 8, median(X(:,3)), st.meanranks(3)});
%!test
%! ## Each subject ranks the three measurements, so the mean ranks sum to 6
%! assert_equal (sum (cell2mat (C(4:6,4))), 6, 1e-12);
%!test
%! assert_equal (C(8,1:6), {'Source', 'SS', 'DoF', 'MS', 'Chi-sq', ...
%!                          'Prob>Chi-sq'});
%!test
%! assert_equal (C(9:11,:), [tbl(2:4,:), cell(3, 2)]);
%!test
%! assert_equal (C(13,1), {'Multiple comparisons (holm, alpha 0.05)'});
%!test
%! assert_equal (C(14,:), {'Measurement', 'Measurement', 'Lower bound', ...
%!                         'Mean rank difference', 'Upper bound', ...
%!                         'Statistic', 'DoF', 'Adjusted p-value'});
%!test
%! assert_equal (C(15:17,3:8), num2cell (c(:,[3, 4, 5, 7, 8, 6])));

%!test
%! R = octave_calc_friedman (X.', 'rows');
%! assert_equal (R(4,1:3), {'Row 1', 8, median(X(:,1))});

%!test
%! R = octave_calc_friedman (X, 'columns', {'Low', 'High', 'Middle'});
%! assert_equal (R(4:6,1), {'Low'; 'High'; 'Middle'});

%!test
%! D = [X; 20, NaN, 22];
%! R = octave_calc_friedman (D, 'columns');
%! s = 'One subject was left out for a missing measurement.';
%! assert_equal (R(3,1), {s});
%!test
%! D = [X; 20, NaN, 22];
%! R = octave_calc_friedman (D, 'columns');
%! assert_equal (R(6,2), {8});

%!test
%! R = octave_calc_friedman (X, 'columns', [], 'bonferroni', 0.01);
%! assert_equal (R(13,1), {'Multiple comparisons (bonferroni, alpha 0.01)'});

%!test
%! ## Two measurements are allowed, and give one comparison
%! R = octave_calc_friedman (X(:,1:2), 'columns');
%! assert_equal (rows (R), 14);

%!error<octave_calc_friedman: invalid number of input arguments.> ...
%! octave_calc_friedman ([1, 2])
%!error<octave_calc_friedman: CTYPE must be 'bonferroni', 'scheffe', 'mvt', 'holm', 'hochberg', 'fdr' or 'lsd'.> ...
%! octave_calc_friedman ([1, 2; 3, 4], 'columns', [], 'tukey')
%!error<octave_calc_friedman: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_friedman ([1, 2; 3, 4], 'columns', [], 'holm', 1)
%!error<octave_calc_friedman: BY must be 'columns' or 'rows'.> ...
%! octave_calc_friedman ([1, 2], 'labels')
%!error<octave_calc_friedman: DATA must be a real numeric matrix.> ...
%! octave_calc_friedman ('ab', 'columns')
%!error<octave_calc_friedman: the input range holds fewer than two measurements.> ...
%! octave_calc_friedman ([1; 2], 'columns')
%!error<octave_calc_friedman: two measurements share the name 'A'.> ...
%! octave_calc_friedman ([1, 2; 3, 4], 'columns', {'A', 'A'})
%!error<octave_calc_friedman: fewer than two subjects hold every measurement; there is nothing to compare.> ...
%! octave_calc_friedman ([1, 2; 3, NaN], 'columns')
