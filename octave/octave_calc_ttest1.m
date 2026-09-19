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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_ttest1 (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ttest1 (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ttest1 (@var{DATA}, @var{BY}, @var{NAMES}, @var{NULLMEAN})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ttest1 (@var{DATA}, @var{BY}, @var{NAMES}, @var{NULLMEAN}, @var{TAIL})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_ttest1 (@var{DATA}, @var{BY}, @var{NAMES}, @var{NULLMEAN}, @var{TAIL}, @var{ALPHA})
##
## One-sample t-test for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_ttest1 (@var{DATA}, @var{BY})} runs
## @code{ttest} on the one sample in @var{DATA} against a mean of zero,
## ignoring @code{NaN}, which stands for an empty cell.  @var{BY} says how
## @var{DATA} holds the sample, @qcode{'columns'}, one column of values, or
## @qcode{'rows'}, one row of them, and @var{NAMES} names it.
##
## @var{NULLMEAN} is the mean the sample is tested against, 0 by default.
## @var{TAIL} is @qcode{'both'}, the default, @qcode{'right'}, which tests
## whether the sample's mean is the greater, or @qcode{'left'}, whether it is
## the smaller.  @var{ALPHA} is the significance level, 0.05 by default; all
## three are named in the heading of the test.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; the sample
## with its count, mean, standard deviation and standard error; and the lower
## bound, estimate and upper bound of the difference between the sample's
## mean and @var{NULLMEAN}, the test statistic, its degrees of freedom, and
## its p-value.
##
## The bounds are of the difference, not of the mean, so that a test of a
## mean of zero reads the same way as the two-sample and paired tests beside
## it.  A one-sided test bounds it on one side only, and the other bound is
## @code{Inf} or @code{-Inf}.
##
## The @code{statistics} package must be loaded.
##
## @seealso{ttest}
## @end deftypefn

function C = octave_calc_ttest1 (DATA, BY, NAMES, NULLMEAN, TAIL, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 6)
    error ("octave_calc_ttest1: invalid number of input arguments.");
  endif
  if (nargin < 3)
    NAMES = [];
  endif
  if (nargin < 4)
    NULLMEAN = 0;
  endif
  if (nargin < 5)
    TAIL = 'both';
  endif
  if (nargin < 6)
    ALPHA = 0.05;
  endif
  if (! (isnumeric (NULLMEAN) && isreal (NULLMEAN) && isscalar (NULLMEAN)
         && ! isnan (NULLMEAN)))
    error ("octave_calc_ttest1: NULLMEAN must be a number.");
  endif
  [tail, errmsg] = octave_calc_tail (TAIL);
  if (! isempty (errmsg))
    error ("octave_calc_ttest1: %s", errmsg);
  endif
  errmsg = octave_calc_alpha (ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_ttest1: %s", errmsg);
  endif

  [x, label, errmsg] = octave_calc_sample (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_ttest1: %s", errmsg);
  endif

  ## The test, against the mean given
  [~, p, ci, stats] = ttest (x, NULLMEAN, 'tail', TAIL, 'alpha', ALPHA);

  ## The cells, eight columns wide.  ttest bounds the mean itself, and the
  ## difference is what the tests beside this one report
  n = numel (x);
  deviation = std (x);
  heading = sprintf ("Difference from %g (%s, alpha %g)", NULLMEAN, tail, ...
                     ALPHA);
  C = [pad('One-sample t-test'); pad(); ...
       pad('Sample', 'Count', 'Mean', 'Standard deviation', ...
           'Standard error'); ...
       pad(label, n, mean (x), deviation, deviation / sqrt (n)); pad(); ...
       pad(heading); ...
       pad('Sample', 'Lower bound', 'Mean difference', 'Upper bound', ...
           'Statistic', 'DoF', 'p-value'); ...
       pad(label, ci(1) - NULLMEAN, mean (x) - NULLMEAN, ci(2) - NULLMEAN, ...
           stats.tstat, stats.df, p)];

endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, x, ci, st, p
%! x = [4.2; 5.1; 3.8; 6.0; 4.9; 5.5; 4.1; 5.8; 4.6; 5.2];
%! [~, p, ci, st] = ttest (x, 0, 'tail', 'both', 'alpha', 0.05);
%! C = octave_calc_ttest1 (x, 'columns');
%!test
%! assert_equal (size (C), [8, 8]);
%!test
%! assert_equal (C(1,1), {'One-sample t-test'});
%!test
%! assert_equal (C(3,:), {'Sample', 'Count', 'Mean', 'Standard deviation', ...
%!                        'Standard error', [], [], []});
%!test
%! assert_equal (C(4,1:3), {'Sample', 10, mean(x)});
%!test
%! assert_equal (C(4,4:5), {std(x), std(x) / sqrt(10)});
%!test
%! assert_equal (C(6,1), {'Difference from 0 (two-sided, alpha 0.05)'});
%!test
%! assert_equal (C(8,1:7), {'Sample', ci(1), mean(x), ci(2), st.tstat, ...
%!                          st.df, p});

%!test
%! ## The bounds are of the difference from the mean tested against
%! R = octave_calc_ttest1 (x, 'columns', [], 5);
%! [~, ~, c5] = ttest (x, 5);
%! assert_equal (R(8,2:4), {c5(1) - 5, mean(x) - 5, c5(2) - 5});
%!test
%! R = octave_calc_ttest1 (x, 'columns', [], 5);
%! assert_equal (R(6,1), {'Difference from 5 (two-sided, alpha 0.05)'});

%!test
%! R = octave_calc_ttest1 (x.', 'rows');
%! assert_equal (R(4,1:2), {'Sample', 10});

%!test
%! R = octave_calc_ttest1 (x, 'columns', {'Yield'});
%! assert_equal (R(4,1), {'Yield'});

%!test
%! ## Empty cells are left out of the count
%! R = octave_calc_ttest1 ([x; NaN], 'columns');
%! assert_equal (R(4,2), {10});

%!test
%! ## A one-sided test leaves the other bound infinite
%! R = octave_calc_ttest1 (x, 'columns', [], 0, 'right');
%! assert_equal (R{8,4}, Inf);
%!test
%! R = octave_calc_ttest1 (x, 'columns', [], 0, 'left', 0.01);
%! assert_equal (R(6,1), {'Difference from 0 (left-sided, alpha 0.01)'});

%!error<octave_calc_ttest1: invalid number of input arguments.> ...
%! octave_calc_ttest1 ([1; 2])
%!error<octave_calc_ttest1: NULLMEAN must be a number.> ...
%! octave_calc_ttest1 ([1; 2], 'columns', [], 'five')
%!error<octave_calc_ttest1: TAIL must be 'both', 'right' or 'left'.> ...
%! octave_calc_ttest1 ([1; 2], 'columns', [], 0, 'upper')
%!error<octave_calc_ttest1: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_ttest1 ([1; 2], 'columns', [], 0, 'both', 1)
%!error<octave_calc_ttest1: BY must be 'columns' or 'rows'.> ...
%! octave_calc_ttest1 ([1; 2], 'labels')
%!error<octave_calc_ttest1: DATA must be a real numeric matrix.> ...
%! octave_calc_ttest1 ('ab', 'columns')
%!error<octave_calc_ttest1: the input range must hold one column of values.> ...
%! octave_calc_ttest1 ([1, 2; 3, 4], 'columns')
%!error<octave_calc_ttest1: the input range must hold one row of values.> ...
%! octave_calc_ttest1 ([1, 2; 3, 4], 'rows')
%!error<octave_calc_ttest1: the sample holds fewer than two numbers.> ...
%! octave_calc_ttest1 ([1; NaN], 'columns')
