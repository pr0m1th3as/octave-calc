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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_isoutlier (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_isoutlier (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_isoutlier (@var{DATA}, @var{BY}, @var{NAMES}, @var{METHOD})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_isoutlier (@var{DATA}, @var{BY}, @var{NAMES}, @var{METHOD}, @var{FACTOR})
##
## Outlier detection for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_isoutlier (@var{DATA}, @var{BY})} runs
## @code{isoutlier} on the one sample in @var{DATA}, ignoring @code{NaN},
## which stands for an empty cell.  @var{BY} says how @var{DATA} holds the
## sample, @qcode{'columns'}, one column of values, or @qcode{'rows'}, one
## row of them, and @var{NAMES} names it.
##
## @var{METHOD} is @qcode{'median'}, the default, @qcode{'mean'},
## @qcode{'quartiles'}, @qcode{'grubbs'} or @qcode{'gesd'}.  @var{FACTOR} is
## how far from the centre a value must lie to be called an outlier, in the
## units each method counts in, and 0 leaves each method its own default,
## which is what it is by default here.  The method and the factor are named
## in the heading.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; the sample
## with its count, how many outliers it holds, the centre the method took and
## the bounds it set; and a row per outlier with its place in the sample, its
## value and how far it sits beyond the nearer bound.
##
## The place is the row of the input range the value came from, counting the
## header where there is one, so that a reader can find it in the sheet.
## Empty cells take a place of their own and are not values.
##
## The @code{statistics} package must be loaded.
##
## @seealso{isoutlier}
## @end deftypefn

function C = octave_calc_isoutlier (DATA, BY, NAMES, METHOD, FACTOR)

  ## Input validation
  if (nargin < 2 || nargin > 5)
    error ("octave_calc_isoutlier: invalid number of input arguments.");
  endif
  if (nargin < 3)
    NAMES = [];
  endif
  if (nargin < 4)
    METHOD = 'median';
  endif
  if (nargin < 5)
    FACTOR = 0;
  endif
  methods = {'median', 'mean', 'quartiles', 'grubbs', 'gesd'};
  if (! (ischar (METHOD) && any (strcmp (METHOD, methods))))
    error (strcat ("octave_calc_isoutlier: METHOD must be 'median',", ...
                   " 'mean', 'quartiles', 'grubbs' or 'gesd'."));
  endif
  if (! (isnumeric (FACTOR) && isreal (FACTOR) && isscalar (FACTOR)
         && FACTOR >= 0))
    error (strcat ("octave_calc_isoutlier: FACTOR must be a number of 0", ...
                   " or more."));
  endif

  [x, label, errmsg] = octave_calc_sample (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_isoutlier: %s", errmsg);
  endif

  ## Where each kept value sat in the input range, so that an outlier can be
  ## found again in the sheet
  if (strcmp (BY, 'rows'))
    place = find (! isnan (DATA.'));
  else
    place = find (! isnan (DATA));
  endif

  ## The detection, leaving each method its own threshold unless one is given
  args = {METHOD};
  if (FACTOR > 0)
    args = [args, {'ThresholdFactor', FACTOR}];
  endif
  [tf, lower, upper, centre] = isoutlier (x, args{:});

  ## The cells, eight columns wide
  if (FACTOR > 0)
    heading = sprintf ("Outliers (%s, factor %g)", METHOD, FACTOR);
  else
    heading = sprintf ("Outliers (%s, the method's own factor)", METHOD);
  endif
  beyond = max (x - upper, lower - x);
  found = find (tf);
  outliers = [num2cell(place(found)), num2cell(x(found)), ...
              num2cell(beyond(found)), cell(numel (found), 5)];
  C = [pad('Outliers'); pad(); ...
       pad('Sample', 'Count', 'Outliers', 'Centre', 'Lower bound', ...
           'Upper bound'); ...
       pad(label, numel (x), sum (tf), centre, lower, upper); pad(); ...
       pad(heading); pad('Row', 'Value', 'Beyond the bound'); outliers];

endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, x
%! x = [4.2; 5.1; 3.8; 6.0; 4.9; 5.5; 4.1; 5.8; 4.6; 5.2; 3.9; 6.3; 4.4; ...
%!      5.0; 12.8];
%! C = octave_calc_isoutlier (x, 'columns', {'Yield'});
%!test
%! assert_equal (size (C), [8, 8]);
%!test
%! assert_equal (C(1,1), {'Outliers'});
%!test
%! assert_equal (C(3,:), {'Sample', 'Count', 'Outliers', 'Centre', ...
%!                        'Lower bound', 'Upper bound', [], []});
%!test
%! [~, l, u, c] = isoutlier (x);
%! assert_equal (C(4,1:6), {'Yield', 15, 1, c, l, u});
%!test
%! assert_equal (C(6,1), {"Outliers (median, the method's own factor)"});
%!test
%! assert_equal (C(7,1:3), {'Row', 'Value', 'Beyond the bound'});
%!test
%! assert_equal (C(8,1:2), {15, 12.8});
%!test
%! [~, ~, u] = isoutlier (x);
%! assert_equal (C(8,3), {12.8 - u});

%!test
%! ## A sample with nothing beyond the bounds lists no rows
%! R = octave_calc_isoutlier (x(1:14), 'columns');
%! assert_equal (rows (R), 7);
%!test
%! R = octave_calc_isoutlier (x(1:14), 'columns');
%! assert_equal (R(4,3), {0});

%!test
%! ## The row is the row of the input range, empty cells counted
%! D = [x(1:3); NaN; x(4:end)];
%! R = octave_calc_isoutlier (D, 'columns');
%! assert_equal (R(8,1), {16});

%!test
%! R = octave_calc_isoutlier (x.', 'rows');
%! assert_equal (R(8,1:2), {15, 12.8});

%!test
%! R = octave_calc_isoutlier (x, 'columns', [], 'quartiles');
%! [~, l, u, c] = isoutlier (x, 'quartiles');
%! assert_equal (R(4,4:6), {c, l, u});
%!test
%! R = octave_calc_isoutlier (x, 'columns', [], 'mean', 2);
%! assert_equal (R(6,1), {'Outliers (mean, factor 2)'});
%!test
%! R = octave_calc_isoutlier (x, 'columns', [], 'mean', 2);
%! [~, l, u] = isoutlier (x, 'mean', 'ThresholdFactor', 2);
%! assert_equal (R(4,5:6), {l, u});

%!error<octave_calc_isoutlier: invalid number of input arguments.> ...
%! octave_calc_isoutlier ([1; 2])
%!error<octave_calc_isoutlier: METHOD must be 'median', 'mean', 'quartiles', 'grubbs' or 'gesd'.> ...
%! octave_calc_isoutlier ([1; 2], 'columns', [], 'hampel')
%!error<octave_calc_isoutlier: FACTOR must be a number of 0 or more.> ...
%! octave_calc_isoutlier ([1; 2], 'columns', [], 'median', -1)
%!error<octave_calc_isoutlier: BY must be 'columns' or 'rows'.> ...
%! octave_calc_isoutlier ([1; 2], 'labels')
%!error<octave_calc_isoutlier: DATA must be a real numeric matrix.> ...
%! octave_calc_isoutlier ('ab', 'columns')
%!error<octave_calc_isoutlier: the input range must hold one column of values.> ...
%! octave_calc_isoutlier ([1, 2; 3, 4], 'columns')
%!error<octave_calc_isoutlier: the sample holds fewer than two numbers.> ...
%! octave_calc_isoutlier ([1; NaN], 'columns')
