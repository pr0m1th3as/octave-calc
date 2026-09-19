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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_normality (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_normality (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_normality (@var{DATA}, @var{BY}, @var{NAMES}, @var{ALPHA})
##
## Tests of normality for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_normality (@var{DATA}, @var{BY})} runs
## @code{adtest}, @code{lillietest}, @code{jbtest} and @code{swtest} on the
## one sample in @var{DATA}, ignoring @code{NaN}, which stands for an empty
## cell.  @var{BY} says how @var{DATA} holds the sample, @qcode{'columns'},
## one column of values, or @qcode{'rows'}, one row of them, and @var{NAMES}
## names it.  @var{ALPHA} is the significance level, 0.05 by default, and is
## named in the heading of the tests.
##
## All four are run and all four are reported, since they weigh different
## departures from normality and a reader who has to choose one beforehand
## cannot know which.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; anything
## the tests could not do, in words; the sample with its count, mean,
## standard deviation, skewness and kurtosis; and a row per test with its
## statistic and its p-value.
##
## @code{lillietest} and @code{jbtest} read their p-value from a table and
## clamp it to the range of that table, and @code{adtest} does the same, so a
## p-value at the edge is a bound and not a measurement.  Each such test is
## named above the results, and a test that could not run at all reports
## @code{NaN} for both figures and is named there too.
##
## The @code{statistics} package must be loaded.
##
## @seealso{adtest, lillietest, jbtest, swtest}
## @end deftypefn

function C = octave_calc_normality (DATA, BY, NAMES, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 4)
    error ("octave_calc_normality: invalid number of input arguments.");
  endif
  if (nargin < 3)
    NAMES = [];
  endif
  if (nargin < 4)
    ALPHA = 0.05;
  endif
  errmsg = octave_calc_alpha (ALPHA);
  if (! isempty (errmsg))
    error ("octave_calc_normality: %s", errmsg);
  endif

  [x, label, errmsg] = octave_calc_sample (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_normality: %s", errmsg);
  endif

  ## The four tests, each reporting what it could not do rather than a
  ## figure that looks like the others
  tests = {'Anderson-Darling', @(v, a) adtest (v, 'alpha', a); ...
           'Lilliefors', @(v, a) lillietest (v, 'alpha', a); ...
           'Jarque-Bera', @(v, a) jbtest (v, a); ...
           'Shapiro-Wilk', @(v, a) swtest (v, 'alpha', a)};
  table = cell (4, 8);
  bounded = {};
  refused = {};
  for ii = 1:4
    [stat, p, note] = attempt (tests{ii,2}, x, ALPHA);
    table(ii,1:3) = {tests{ii,1}, stat, p};
    if (strcmp (note, 'bounded'))
      bounded = [bounded, tests(ii,1)];
    elseif (! isempty (note))
      refused = [refused, {sprintf("%s (%s)", tests{ii,1}, note)}];
    endif
  endfor

  ## The cells, eight columns wide
  C = [pad('Tests of normality'); pad(); ...
       said(strcat ("The p-value of %s is the edge of its table, not a", ...
                    " measurement."), bounded); ...
       said('%s could not be run.', refused); ...
       pad('Sample', 'Count', 'Mean', 'Standard deviation', 'Skewness', ...
           'Kurtosis'); ...
       pad(label, numel (x), mean (x), std (x), skewness (x), ...
           kurtosis (x)); pad(); ...
       pad(sprintf ("Tests of normality (alpha %g)", ALPHA)); ...
       pad('Test', 'Statistic', 'p-value'); table];

endfunction

## One test, with the statistic, the p-value and what it could not do.  A
## p-value read off the end of a table comes with a warning and no other
## sign, so the warning is what says the figure is a bound.  It is matched
## by its words, since lastwarn also catches warnings from far below that
## have nothing to do with the test; the three forms below are the ones
## adtest, lillietest and jbtest raise, each of them asserted upstream.
function [stat, p, note] = attempt (fcn, x, alpha)
  note = "";
  held = lastwarn ();
  lastwarn ("");
  try
    [~, p, stat] = fcn (x, alpha);
    clamped = 'tabulated value|out of range m(in|ax) p-value';
    if (! isempty (regexp (lastwarn (), clamped, "once")))
      note = 'bounded';
    endif
  catch err
    stat = NaN;
    p = NaN;
    note = strtrim (regexprep (err.message, '^[^:]*:', ''));
  end_try_catch
  lastwarn (held);
endfunction

## A sentence naming the tests it is about, and a blank line, or nothing
## where there are none
function R = said (form, which)
  R = cell (0, 8);
  if (isempty (which))
    return;
  endif
  R = cell (2, 8);
  R{1,1} = sprintf (form, strjoin (which, ", "));
endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, x
%! x = [4.2; 5.1; 3.8; 6.0; 4.9; 5.5; 4.1; 5.8; 4.6; 5.2; 3.9; 6.3; 4.4; ...
%!      5.0; 4.8];
%! C = octave_calc_normality (x, 'columns', {'Yield'});
%!test
%! assert_equal (columns (C), 8);
%!test
%! assert_equal (C(1,1), {'Tests of normality'});
%!test
%! assert_equal (C(end-8,:), {'Sample', 'Count', 'Mean', ...
%!                            'Standard deviation', 'Skewness', 'Kurtosis', ...
%!                            [], []});
%!test
%! assert_equal (C(end-7,1:4), {'Yield', 15, mean(x), std(x)});
%!test
%! assert_equal (C(end-7,5:6), {skewness(x), kurtosis(x)});
%!test
%! assert_equal (C(end-4,1:3), {'Test', 'Statistic', 'p-value'});
%!test
%! assert_equal (C(end-3:end,1), {'Anderson-Darling'; 'Lilliefors'; ...
%!                                'Jarque-Bera'; 'Shapiro-Wilk'});

%!test
%! ## All four tests are reported, whatever any one of them says
%! assert_equal (rows (C) >= 9, true);
%!test
%! [~, p, s] = swtest (x, 'alpha', 0.05);
%! assert_equal (C(end,2:3), {s, p});

%!test
%! ## A p-value read off the end of a table is named as a bound
%! s = strcat ('The p-value of Lilliefors, Jarque-Bera is the edge of', ...
%!              ' its table, not a measurement.');
%! assert_equal (C(3,1), {s});

%!test
%! R = octave_calc_normality (x.', 'rows');
%! assert_equal (R(end-7,1:2), {'Sample', 15});

%!test
%! R = octave_calc_normality (x, 'columns', [], 0.01);
%! assert_equal (R(end-5,1), {'Tests of normality (alpha 0.01)'});

%!test
%! ## A test that cannot run reports NaN and is named, and the rest still run
%! R = octave_calc_normality ([1; 2; 3], 'columns');
%! assert_equal (R{end-3,2}, NaN);
%!test
%! R = octave_calc_normality ([1; 2; 3], 'columns');
%! assert_equal (isnan (cell2mat (R(end,2:3))), [false, false]);

%!error<octave_calc_normality: invalid number of input arguments.> ...
%! octave_calc_normality ([1; 2])
%!error<octave_calc_normality: ALPHA must be a number greater than 0 and less than 1.> ...
%! octave_calc_normality ([1; 2], 'columns', [], 1)
%!error<octave_calc_normality: BY must be 'columns' or 'rows'.> ...
%! octave_calc_normality ([1; 2], 'labels')
%!error<octave_calc_normality: DATA must be a real numeric matrix.> ...
%! octave_calc_normality ('ab', 'columns')
%!error<octave_calc_normality: the input range must hold one column of values.> ...
%! octave_calc_normality ([1, 2; 3, 4], 'columns')
%!error<octave_calc_normality: the sample holds fewer than two numbers.> ...
%! octave_calc_normality ([1; NaN], 'columns')
