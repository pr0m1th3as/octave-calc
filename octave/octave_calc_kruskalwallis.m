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

function C = octave_calc_kruskalwallis (DATA, BY, NAMES)

  ## Input validation
  if (nargin < 2 || nargin > 3)
    error ("octave_calc_kruskalwallis: invalid number of input arguments.");
  endif
  if (! (ischar (BY) && any (strcmp (BY, {'columns', 'rows', 'labels'}))))
    error (strcat ("octave_calc_kruskalwallis: BY must be 'columns',", ...
                   " 'rows' or 'labels'."));
  endif

  if (nargin < 3)
    NAMES = [];
  endif
  if (strcmp (BY, 'labels'))
    if (! isempty (NAMES))
      error (strcat ("octave_calc_kruskalwallis: NAMES applies only to", ...
                     " groups in columns or rows."));
    endif
    [x, group, labels] = labelled (DATA);
  else
    [x, group, labels] = samples (DATA, BY, NAMES);
  endif
  k = numel (labels);
  if (k < 2)
    error (strcat ("octave_calc_kruskalwallis: the input range holds", ...
                   " fewer than two groups."));
  endif

  ## The test, and the pairwise comparisons of its mean ranks
  [~, tbl, stats] = kruskalwallis (x, group, 'off');
  c = multcompare (stats, 'ctype', 'holm', 'display', 'off');
  medians = accumarray (group, x, [], @median);

  ## The cells, six columns wide
  groups = [labels, num2cell(stats.n(:)), num2cell(medians), ...
            num2cell(stats.meanranks(:)), cell(k, 2)];
  pairs = [labels(c(:,1)), labels(c(:,2)), num2cell(c(:,3:6))];
  C = [pad('Kruskal-Wallis Test'); pad(); ...
       pad('Groups', 'Count', 'Median', 'Mean rank'); groups; pad(); ...
       tbl; pad(); pad('Multiple comparisons (Holm)'); ...
       pad('Group', 'Group', 'Lower bound', 'Mean rank difference', ...
           'Upper bound', 'Adjusted p-value'); pairs];

endfunction

## Every value in one column, beside the number of its group, from one group
## per column or per row, named after NAMES where it names them
function [x, group, labels] = samples (DATA, BY, NAMES)
  if (! (isnumeric (DATA) && isreal (DATA) && ismatrix (DATA)))
    error ("octave_calc_kruskalwallis: DATA must be a real numeric matrix.");
  endif
  if (strcmp (BY, 'rows'))
    DATA = DATA.';
    stem = 'Row';
  else
    stem = 'Column';
  endif
  k = columns (DATA);
  labels = arrayfun (@(ii) sprintf ("%s %d", stem, ii), (1:k)', ...
                     "UniformOutput", false);
  if (! isempty (NAMES))
    names = texts (NAMES, "NAMES");
    if (numel (names) != k)
      error (strcat ("octave_calc_kruskalwallis: NAMES must hold one", ...
                     " name for each group."));
    endif
    given = ! cellfun (@isempty, names);
    labels(given) = names(given);
    [~, first] = unique (labels, "first");
    if (numel (first) < k)
      twice = labels{setdiff (1:k, first)(1)};
      error (strcat ("octave_calc_kruskalwallis: two groups share the", ...
                     " name '%s'."), twice);
    endif
  endif
  x = [];
  group = [];
  for ii = 1:k
    values = DATA(! isnan (DATA(:,ii)), ii);
    if (isempty (values) && k > 1)
      error (strcat ("octave_calc_kruskalwallis: the group '%s' holds", ...
                     " no numbers."), labels{ii});
    endif
    x = [x; values];
    group = [group; repmat(ii, numel (values), 1)];
  endfor
endfunction

## Every value in one column, beside the number of its group, from values
## beside their group labels
function [x, group, labels] = labelled (DATA)
  if (! (ismatrix (DATA) && columns (DATA) == 2
         && ((isnumeric (DATA) && isreal (DATA)) || iscell (DATA))))
    error (strcat ("octave_calc_kruskalwallis: DATA must have two", ...
                   " columns, the values and their group labels."));
  endif
  if (isnumeric (DATA))
    x = DATA(:,1);
  else
    number = @(v) isnumeric (v) && isreal (v) && isscalar (v);
    if (! all (cellfun (@(v) number (v) || isempty (v), DATA(:,1))))
      error (strcat ("octave_calc_kruskalwallis: the values in DATA must", ...
                     " be numbers."));
    endif
    x = nan (rows (DATA), 1);
    present = ! cellfun (@isempty, DATA(:,1));
    x(present) = [DATA{present,1}];
  endif
  keep = ! isnan (x);
  if (isnumeric (DATA))
    names = DATA(keep,2);
    missing = isnan (names);
  else
    names = texts (DATA(keep,2), "the group labels in DATA");
    missing = cellfun (@isempty, names);
  endif
  if (any (missing))
    error (strcat ("octave_calc_kruskalwallis: the input range holds a", ...
                   " value with no group label."));
  endif
  x = x(keep);
  if (isempty (x))
    group = [];
    labels = cell (0, 1);
  else
    [group, labels] = grp2idx (names);
  endif
endfunction

## Names as a column of text, from a numeric vector or a cell array of text,
## numbers and empty values; a missing name is empty text
function names = texts (V, what)
  if (isnumeric (V) && isreal (V))
    V = num2cell (V);
  endif
  isname = @(v) (isnumeric (v) && isreal (v) && isscalar (v)) || isempty (v) ...
                || (ischar (v) && rows (v) <= 1);
  if (! (iscell (V) && all (cellfun (isname, V(:)))))
    error ("octave_calc_kruskalwallis: %s must be text or numbers.", what);
  endif
  names = cell (numel (V), 1);
  for ii = 1:numel (V)
    v = V{ii};
    if (ischar (v))
      names{ii} = v;
    elseif (! (isempty (v) || isnan (v)))
      names{ii} = num2str (v);
    else
      names{ii} = '';
    endif
  endfor
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
%! assert_equal (C(13,1), {'Multiple comparisons (Holm)'});
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
