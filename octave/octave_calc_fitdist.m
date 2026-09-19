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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_fitdist (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_fitdist (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_fitdist (@var{DATA}, @var{BY}, @var{NAMES}, @var{DISTNAME})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_fitdist (@var{DATA}, @var{BY}, @var{NAMES}, @var{DISTNAME}, @var{CURVE})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_fitdist (@var{DATA}, @var{BY}, @var{NAMES}, @var{DISTNAME}, @var{CURVE}, @var{ALPHA})
##
## Distribution fitting for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_fitdist (@var{DATA}, @var{BY})} fits a normal
## distribution to the one sample in @var{DATA} with @code{fitdist},
## ignoring @code{NaN}, which stands for an empty cell.  @var{BY} says how
## @var{DATA} holds the sample, @qcode{'columns'}, one column of values, or
## @qcode{'rows'}, one row of them, and @var{NAMES} names it.
##
## @var{DISTNAME} is any distribution @code{fitdist} takes, @qcode{'Normal'}
## by default.  @var{ALPHA} sets the confidence intervals of the estimates,
## 0.05 by default, and is named in the heading.
##
## @var{CURVE} is @qcode{'none'}, the default, which writes the fit alone;
## @qcode{'sample'}, which follows it with the density and the cumulative
## probability of the fitted distribution at each value of the sample, in
## order; or @qcode{'grid'}, which does the same over one hundred evenly
## spaced points from the smallest value to the largest.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; the sample
## with its count and its own mean, standard deviation, smallest and largest
## value; a row per fitted parameter with its estimate and the bounds of its
## interval; the fitted distribution's negative log likelihood, mean,
## standard deviation and median; and the curve where one was asked for.
##
## A distribution fitted without parameters, as a kernel is, says so in place
## of the parameter table.
##
## The @code{statistics} package must be loaded.
##
## @seealso{fitdist, paramci}
## @end deftypefn

function C = octave_calc_fitdist (DATA, BY, NAMES, DISTNAME, CURVE, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 6)
    error ("octave_calc_fitdist: invalid number of input arguments.");
  endif
  if (nargin < 3)
    NAMES = [];
  endif
  if (nargin < 4)
    DISTNAME = 'Normal';
  endif
  if (nargin < 5)
    CURVE = 'none';
  endif
  if (nargin < 6)
    ALPHA = 0.05;
  endif
  if (! (ischar (DISTNAME) && any (strcmpi (DISTNAME, fitdist ()))))
    error (strcat ("octave_calc_fitdist: DISTNAME must be a distribution", ...
                   " fitdist takes."));
  endif
  if (! (ischar (CURVE) && any (strcmp (CURVE, {'none', 'sample', 'grid'}))))
    error (strcat ("octave_calc_fitdist: CURVE must be 'none', 'sample'", ...
                   " or 'grid'."));
  endif
  errmsg = octave_calc_alpha (ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_fitdist: %s", errmsg);
  endif

  [x, label, errmsg] = octave_calc_sample (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_fitdist: %s", errmsg);
  endif

  ## The fit, under the name the user chose rather than the one fitdist
  ## raises it under
  try
    pd = fitdist (x, DISTNAME);
  catch err
    error ("octave_calc_fitdist: %s", ...
           strtrim (regexprep (err.message, '^[^:]*:', '')));
  end_try_catch

  ## The estimates and their intervals, or a word where there are none
  if (pd.NumParameters > 0)
    ci = paramci (pd, 'Alpha', ALPHA);
    estimates = [pd.ParameterNames(:), num2cell(pd.ParameterValues(:)), ...
                 num2cell(ci(1,:)(:)), num2cell(ci(2,:)(:)), ...
                 cell(pd.NumParameters, 4)];
    header = pad ('Parameter', 'Estimate', 'Lower bound', 'Upper bound');
  else
    estimates = pad (sprintf ("%s is fitted without parameters.", ...
                              pd.DistributionName));
    header = cell (0, 8);
  endif

  ## The cells, eight columns wide
  C = [pad('Distribution fitting'); pad(); ...
       pad('Sample', 'Count', 'Mean', 'Standard deviation', 'Minimum', ...
           'Maximum'); ...
       pad(label, numel (x), mean (x), std (x), min (x), max (x)); pad(); ...
       pad(sprintf ("%s fitted to %s (alpha %g)", pd.DistributionName, ...
                    label, ALPHA)); ...
       header; estimates; pad(); ...
       pad('Negative log likelihood', negloglik (pd)); ...
       pad('Mean of the fit', mean (pd)); ...
       pad('Standard deviation of the fit', std (pd)); ...
       pad('Median of the fit', median (pd)); curve(pd, x, CURVE)];

endfunction

## The density and the cumulative probability of the fit, over the sample in
## order or over an even grid across it
function R = curve (pd, x, CURVE)
  R = cell (0, 8);
  if (strcmp (CURVE, 'none'))
    return;
  endif
  if (strcmp (CURVE, 'sample'))
    at = sort (x);
  else
    at = linspace (min (x), max (x), 100)(:);
  endif
  R = [pad(); pad(sprintf ("The fit at %d points", numel (at))); ...
       pad('Value', 'Probability density', 'Cumulative probability'); ...
       num2cell(at), num2cell(pdf (pd, at)), num2cell(cdf (pd, at)), ...
       cell(numel (at), 5)];
endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, x, pd
%! x = [4.2; 5.1; 3.8; 6.0; 4.9; 5.5; 4.1; 5.8; 4.6; 5.2; 3.9; 6.3; 4.4; ...
%!      5.0; 4.8];
%! pd = fitdist (x, 'Normal');
%! C = octave_calc_fitdist (x, 'columns', {'Yield'});
%!test
%! assert_equal (size (C), [14, 8]);
%!test
%! assert_equal (C(1,1), {'Distribution fitting'});
%!test
%! assert_equal (C(3,:), {'Sample', 'Count', 'Mean', 'Standard deviation', ...
%!                        'Minimum', 'Maximum', [], []});
%!test
%! assert_equal (C(4,1:6), {'Yield', 15, mean(x), std(x), min(x), max(x)});
%!test
%! assert_equal (C(6,1), {'Normal fitted to Yield (alpha 0.05)'});
%!test
%! assert_equal (C(7,1:4), {'Parameter', 'Estimate', 'Lower bound', ...
%!                          'Upper bound'});
%!test
%! assert_equal (C(8:9,1), {'mu'; 'sigma'});
%!test
%! assert_equal (C(8:9,2), num2cell (pd.ParameterValues(:)));
%!test
%! ci = paramci (pd, 'Alpha', 0.05);
%! assert_equal (C(8:9,3:4), num2cell (ci.'));
%!test
%! assert_equal (C(11,1:2), {'Negative log likelihood', negloglik(pd)});
%!test
%! assert_equal (C(12,1:2), {'Mean of the fit', mean(pd)});
%!test
%! assert_equal (C(end,1:2), {'Median of the fit', median(pd)});

%!test
%! ## A tighter interval moves the bounds and says so
%! R = octave_calc_fitdist (x, 'columns', {'Yield'}, 'Normal', 'none', 0.01);
%! assert_equal (R(6,1), {'Normal fitted to Yield (alpha 0.01)'});
%!test
%! R = octave_calc_fitdist (x, 'columns', [], 'Normal', 'none', 0.01);
%! ci = paramci (pd, 'Alpha', 0.01);
%! assert_equal (R(8:9,3:4), num2cell (ci.'));

%!test
%! ## The curve over the sample is one row per value, in order
%! R = octave_calc_fitdist (x, 'columns', [], 'Normal', 'sample');
%! assert_equal (rows (R), 14 + 3 + 15);
%!test
%! R = octave_calc_fitdist (x, 'columns', [], 'Normal', 'sample');
%! assert_equal (R(end-14:end,1), num2cell (sort (x)));
%!test
%! R = octave_calc_fitdist (x, 'columns', [], 'Normal', 'sample');
%! assert_equal (R(end,2:3), {pdf(pd, max(x)), cdf(pd, max(x))});
%!test
%! R = octave_calc_fitdist (x, 'columns', [], 'Normal', 'grid');
%! assert_equal (rows (R), 14 + 3 + 100);
%!test
%! R = octave_calc_fitdist (x, 'columns', [], 'Normal', 'grid');
%! assert_equal (R(end-99,1), {min(x)});

%!test
%! ## Another distribution names its own parameters
%! R = octave_calc_fitdist (x, 'columns', [], 'Weibull');
%! assert_equal (R(8:9,1), {'A'; 'B'});

%!test
%! ## A kernel is fitted without parameters and says so
%! R = octave_calc_fitdist (x, 'columns', [], 'Kernel');
%! assert_equal (R(7,1), {'Kernel is fitted without parameters.'});

%!test
%! R = octave_calc_fitdist (x.', 'rows');
%! assert_equal (R(4,1:2), {'Sample', 15});

%!error<octave_calc_fitdist: invalid number of input arguments.> ...
%! octave_calc_fitdist ([1; 2])
%!error<octave_calc_fitdist: DISTNAME must be a distribution fitdist takes.> ...
%! octave_calc_fitdist ([1; 2], 'columns', [], 'Loguniform')
%!error<octave_calc_fitdist: CURVE must be 'none', 'sample' or 'grid'.> ...
%! octave_calc_fitdist ([1; 2], 'columns', [], 'Normal', 'both')
%!error<octave_calc_fitdist: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_fitdist ([1; 2], 'columns', [], 'Normal', 'none', 1)
%!error<octave_calc_fitdist: BY must be 'columns' or 'rows'.> ...
%! octave_calc_fitdist ([1; 2], 'labels')
%!error<octave_calc_fitdist: DATA must be a real numeric matrix.> ...
%! octave_calc_fitdist ('ab', 'columns')
%!error<octave_calc_fitdist: the sample holds fewer than two numbers.> ...
%! octave_calc_fitdist ([1; NaN], 'columns')
