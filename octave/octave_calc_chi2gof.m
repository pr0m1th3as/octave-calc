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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_chi2gof (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_chi2gof (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_chi2gof (@var{DATA}, @var{BY}, @var{NAMES}, @var{DISTNAME})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_chi2gof (@var{DATA}, @var{BY}, @var{NAMES}, @var{DISTNAME}, @var{NBINS})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_chi2gof (@var{DATA}, @var{BY}, @var{NAMES}, @var{DISTNAME}, @var{NBINS}, @var{ALPHA})
##
## Goodness of fit for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_chi2gof (@var{DATA}, @var{BY})} fits a normal
## distribution to the one sample in @var{DATA} and tests with
## @code{chi2gof} whether the sample follows it, ignoring @code{NaN}, which
## stands for an empty cell.  @var{BY} says how @var{DATA} holds the sample,
## @qcode{'columns'}, one column of values, or @qcode{'rows'}, one row of
## them, and @var{NAMES} names it.
##
## @var{DISTNAME} is any distribution @code{fitdist} takes, @qcode{'Normal'}
## by default.  @var{NBINS} is how many bins to count the sample into, 10 by
## default.  @var{ALPHA} is the significance level, 0.05 by default; the
## distribution and the significance level are named in the heading.
##
## The distribution is fitted first and the counts each bin is expected to
## hold come from the fitted distribution's own @code{cdf}, so that no
## distribution needs its parameters read in any particular order.  The bins
## are of equal width across the sample, with the outer two reaching to
## infinity.  @code{chi2gof} then joins neighbouring bins until each expects
## enough to be counted, so the bins it used may be fewer than @var{NBINS}.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; the sample
## with its count, mean, standard deviation, smallest and largest value; the
## test with its statistic, degrees of freedom and p-value; and a row per bin
## with its edges, how many values it holds and how many the fit expects.
##
## A test needs more bins than it has estimated parameters, or there is
## nothing left to weigh the fit against; where that is so this refuses and
## says how many bins survived.  Asking for more is not always the answer:
## narrower bins expect fewer values each, so more of them are joined, and a
## sample can end with fewer counted bins than a coarser division gave it.
##
## The @code{statistics} package must be loaded.
##
## @seealso{chi2gof, fitdist}
## @end deftypefn

function C = octave_calc_chi2gof (DATA, BY, NAMES, DISTNAME, NBINS, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 6)
    error ("octave_calc_chi2gof: invalid number of input arguments.");
  endif
  if (nargin < 3)
    NAMES = [];
  endif
  if (nargin < 4)
    DISTNAME = 'Normal';
  endif
  if (nargin < 5)
    NBINS = 10;
  endif
  if (nargin < 6)
    ALPHA = 0.05;
  endif
  if (! (ischar (DISTNAME) && any (strcmpi (DISTNAME, fitdist ()))))
    error (strcat ("octave_calc_chi2gof: DISTNAME must be a distribution", ...
                   " fitdist takes."));
  endif
  if (! (isnumeric (NBINS) && isreal (NBINS) && isscalar (NBINS)
         && NBINS == fix (NBINS) && NBINS >= 2))
    error (strcat ("octave_calc_chi2gof: NBINS must be a whole number of", ...
                   " 2 or more."));
  endif
  errmsg = octave_calc_alpha (ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_chi2gof: %s", errmsg);
  endif

  [x, label, errmsg] = octave_calc_sample (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_chi2gof: %s", errmsg);
  endif

  ## The fit, under the name the user chose
  try
    pd = fitdist (x, DISTNAME);
  catch err
    error ("octave_calc_chi2gof: %s", ...
           strtrim (regexprep (err.message, '^[^:]*:', '')));
  end_try_catch

  ## Bins of equal width across the sample, reaching to infinity at the ends
  ## so that every value falls in one, and the counts the fit expects, read
  ## from the fitted distribution rather than from a named cdf and its
  ## parameters in some order
  edges = linspace (min (x), max (x), NBINS + 1);
  edges(1) = -Inf;
  edges(end) = Inf;
  expected = numel (x) * diff (cdf (pd, edges));
  try
    [~, p, stats] = chi2gof (x, 'edges', edges, 'expected', expected, ...
                             'nparams', pd.NumParameters, 'alpha', ALPHA);
  catch err
    error ("octave_calc_chi2gof: %s", ...
           strtrim (regexprep (err.message, '^[^:]*:', '')));
  end_try_catch
  if (stats.df < 1)
    error (strcat ("octave_calc_chi2gof: the bins that held enough values", ...
                   " leave no degrees of freedom, %d of the %d asked for", ...
                   " having been joined to their neighbours."), ...
           numel (stats.O), NBINS);
  endif

  ## The cells, eight columns wide
  used = numel (stats.O);
  bins = [num2cell((1:used)'), num2cell(stats.edges(1:end-1)(:)), ...
          num2cell(stats.edges(2:end)(:)), num2cell(stats.O(:)), ...
          num2cell(stats.E(:)), cell(used, 3)];
  C = [pad('Goodness of fit'); pad(); ...
       pad('Sample', 'Count', 'Mean', 'Standard deviation', 'Minimum', ...
           'Maximum'); ...
       pad(label, numel (x), mean (x), std (x), min (x), max (x)); pad(); ...
       pad(sprintf ("%s fitted to %s, chi-square test (alpha %g)", ...
                    pd.DistributionName, label, ALPHA)); ...
       pad('Statistic', stats.chi2stat); pad('DoF', stats.df); ...
       pad('p-value', p); pad('Bins asked for', NBINS); ...
       pad('Bins counted', used); pad(); ...
       pad('Bin', 'From', 'To', 'Observed', 'Expected'); bins];

endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, x, pd
%! x = [4.2; 5.1; 3.8; 6.0; 4.9; 5.5; 4.1; 5.8; 4.6; 5.2; 3.9; 6.3; 4.4; ...
%!      5.0; 4.8; 5.3; 4.7; 5.6; 4.0; 5.9; 4.3; 5.4; 4.5; 5.7; 4.85];
%! pd = fitdist (x, 'Normal');
%! C = octave_calc_chi2gof (x, 'columns', {'Yield'}, 'Normal', 6);
%!test
%! assert_equal (columns (C), 8);
%!test
%! assert_equal (C(1,1), {'Goodness of fit'});
%!test
%! assert_equal (C(3,:), {'Sample', 'Count', 'Mean', 'Standard deviation', ...
%!                        'Minimum', 'Maximum', [], []});
%!test
%! assert_equal (C(4,1:2), {'Yield', 25});
%!test
%! assert_equal (C(6,1), ...
%!               {'Normal fitted to Yield, chi-square test (alpha 0.05)'});
%!test
%! assert_equal (C(7:11,1), {'Statistic'; 'DoF'; 'p-value'; ...
%!                           'Bins asked for'; 'Bins counted'});
%!test
%! assert_equal (C(10,2), {6});
%!test
%! assert_equal (C(13,1:5), {'Bin', 'From', 'To', 'Observed', 'Expected'});
%!test
%! ## Every value of the sample falls in a bin
%! assert_equal (sum (cell2mat (C(14:end,4))), 25);
%!test
%! ## The outer bins reach to infinity, so nothing falls outside them
%! assert_equal (C{14,2}, -Inf);
%!test
%! assert_equal (C{end,3}, Inf);
%!test
%! ## The expected counts come from the fit and add to the sample
%! assert_equal (sum (cell2mat (C(14:end,5))), 25, 1e-9);
%!test
%! assert_equal (C{11,2}, rows (C) - 13);

%!test
%! ## The bins counted may be fewer than the bins asked for
%! assert_equal (C{11,2} < C{10,2}, true);

%!test
%! R = octave_calc_chi2gof (x.', 'rows', [], 'Normal', 6);
%! assert_equal (R(4,1:2), {'Sample', 25});

%!test
%! ## Another distribution is fitted and tested the same way
%! R = octave_calc_chi2gof (x, 'columns', [], 'Weibull', 6);
%! assert_equal (R(6,1), ...
%!               {'Weibull fitted to Sample, chi-square test (alpha 0.05)'});

%!error<octave_calc_chi2gof: invalid number of input arguments.> ...
%! octave_calc_chi2gof ([1; 2])
%!error<octave_calc_chi2gof: DISTNAME must be a distribution fitdist takes.> ...
%! octave_calc_chi2gof ([1; 2], 'columns', [], 'Loguniform')
%!error<octave_calc_chi2gof: NBINS must be a whole number of 2 or more.> ...
%! octave_calc_chi2gof ([1; 2], 'columns', [], 'Normal', 1)
%!error<octave_calc_chi2gof: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_chi2gof ([1; 2], 'columns', [], 'Normal', 10, 1)
%!error<octave_calc_chi2gof: BY must be 'columns' or 'rows'.> ...
%! octave_calc_chi2gof ([1; 2], 'labels')
%!error<octave_calc_chi2gof: DATA must be a real numeric matrix.> ...
%! octave_calc_chi2gof ('ab', 'columns')
%!error<octave_calc_chi2gof: the sample holds fewer than two numbers.> ...
%! octave_calc_chi2gof ([1; NaN], 'columns')
%!error<octave_calc_chi2gof: the bins that held enough values leave no degrees of freedom, 2 of the 3 asked for having been joined to their neighbours.> ...
%! octave_calc_chi2gof ([1; 2; 3; 4; 5], 'columns', [], 'Normal', 3)
