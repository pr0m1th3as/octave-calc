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
## @deftypefn {octave-calc} {@var{C} =} octave_calc_kruskalwallis (@var{DATA}, @var{BY})
##
## Kruskal-Wallis Test for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_kruskalwallis (@var{DATA}, @var{BY})} runs
## @code{kruskalwallis} on the numeric matrix @var{DATA}, one sample per column
## when @var{BY} is @qcode{'columns'} and one per row when it is
## @qcode{'rows'}, ignoring @code{NaN}, which stands for an empty cell.  The
## test is followed by the pairwise comparisons of the mean ranks from
## @code{multcompare}, with Holm's adjustment of the p-values.
##
## @var{C} is a cell array of scalars, text and empty values, six columns wide,
## laid out as the cells written into the sheet: the title; each group with its
## count, median and mean rank; the table returned by @code{kruskalwallis}; and
## each pair of groups with the lower bound, estimate and upper bound of their
## difference in mean ranks and its adjusted p-value.  The groups are named
## after their place in the input range, @qcode{'Column 1'}, @qcode{'Column 2'}
## and so on, or @qcode{'Row 1'} and so on.
##
## The @code{statistics} package must be loaded.
##
## @seealso{kruskalwallis, multcompare}
## @end deftypefn

function C = octave_calc_kruskalwallis (DATA, BY)

  ## Input validation
  if (nargin != 2)
    error ("octave_calc_kruskalwallis: invalid number of input arguments.");
  endif
  if (! (isnumeric (DATA) && isreal (DATA) && ismatrix (DATA)))
    error ("octave_calc_kruskalwallis: DATA must be a real numeric matrix.");
  endif
  if (! (ischar (BY) && any (strcmp (BY, {'columns', 'rows'}))))
    error ("octave_calc_kruskalwallis: BY must be 'columns' or 'rows'.");
  endif

  ## One sample per column, rows turned into columns first
  if (strcmp (BY, 'rows'))
    DATA = DATA.';
    stem = 'Row';
  else
    stem = 'Column';
  endif
  k = columns (DATA);
  if (k < 2)
    error (strcat ("octave_calc_kruskalwallis: the input range holds", ...
                   " fewer than two groups."));
  endif

  ## Every value in one column, beside the number of its group
  x = [];
  group = [];
  labels = cell (k, 1);
  for ii = 1:k
    labels{ii} = sprintf ("%s %d", stem, ii);
    values = DATA(! isnan (DATA(:,ii)), ii);
    if (isempty (values))
      error (strcat ("octave_calc_kruskalwallis: the input range holds", ...
                     " no numbers in %s."), labels{ii});
    endif
    n = numel (values);
    x = [x; values];
    group = [group; repmat(ii, n, 1)];
  endfor

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

%!error<octave_calc_kruskalwallis: invalid number of input arguments.> ...
%! octave_calc_kruskalwallis ([1, 2])
%!error<octave_calc_kruskalwallis: DATA must be a real numeric matrix.> ...
%! octave_calc_kruskalwallis ('ab', 'columns')
%!error<octave_calc_kruskalwallis: BY must be 'columns' or 'rows'.> ...
%! octave_calc_kruskalwallis ([1, 2], 'diagonal')
%!error<octave_calc_kruskalwallis: the input range holds fewer than two groups.> ...
%! octave_calc_kruskalwallis ([1; 2], 'columns')
%!error<octave_calc_kruskalwallis: the input range holds no numbers in Column 2.> ...
%! octave_calc_kruskalwallis ([1, NaN; 2, NaN], 'columns')
