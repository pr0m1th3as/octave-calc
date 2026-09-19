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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_anova2 (@var{DATA}, @var{BY})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_anova2 (@var{DATA}, @var{BY}, @var{NAMES})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_anova2 (@var{DATA}, @var{BY}, @var{NAMES}, @var{MODEL})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_anova2 (@var{DATA}, @var{BY}, @var{NAMES}, @var{MODEL}, @var{CTYPE})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_anova2 (@var{DATA}, @var{BY}, @var{NAMES}, @var{MODEL}, @var{CTYPE}, @var{ALPHA})
##
## Two-way ANOVA for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_anova2 (@var{DATA}, @var{BY})} runs
## @code{anovan} on the two factors in @var{DATA}, three columns holding each
## value and the two factors it was measured under, ignoring @code{NaN},
## which stands for an empty cell.  @var{BY} must be @qcode{'labels'} and
## @var{NAMES} names the two factors, which are otherwise @qcode{'Factor 1'}
## and @qcode{'Factor 2'}.
##
## @var{MODEL} is @qcode{'interaction'}, the default, which asks as well
## whether the effect of one factor depends on the level of the other, or
## @qcode{'linear'}, which takes the two effects to add.  @var{CTYPE} is how
## the p-values of the pairwise comparisons are adjusted, @qcode{'holm'} by
## default, and @var{ALPHA} the significance level, 0.05 by default; both are
## named in the heading of each set of comparisons.
##
## @var{C} is a cell array of scalars, text and empty values, eight columns
## wide, laid out as the cells written into the sheet: the title; each
## combination of the two factors with its count, mean and standard
## deviation; the analysis of variance table, a row per factor, the
## interaction where it was asked for, the error and the total; and, for each
## factor in turn, the pairwise comparisons of its levels averaged over the
## other factor.
##
## The interaction needs a combination measured more than once.  Where every
## combination holds at most one value there is nothing left to estimate the
## error from, and @code{anovan} answers with @code{Inf} and @code{NaN}
## rather than saying so, so this refuses instead and says to take the two
## effects as adding.
##
## The @code{statistics} package must be loaded.
##
## @seealso{anovan, multcompare}
## @end deftypefn

function C = octave_calc_anova2 (DATA, BY, NAMES, MODEL, CTYPE, ALPHA)

  ## Input validation
  if (nargin < 2 || nargin > 6)
    error ("octave_calc_anova2: invalid number of input arguments.");
  endif
  if (nargin < 3)
    NAMES = [];
  endif
  if (nargin < 4)
    MODEL = 'interaction';
  endif
  if (nargin < 5)
    CTYPE = 'holm';
  endif
  if (nargin < 6)
    ALPHA = 0.05;
  endif
  if (! (ischar (MODEL) && any (strcmp (MODEL, {'interaction', 'linear'}))))
    error (strcat ("octave_calc_anova2: MODEL must be 'interaction' or", ...
                   " 'linear'."));
  endif

  [y, groups, levels, names, errmsg] = octave_calc_factors (DATA, BY, NAMES);
  if (! isempty (errmsg))
    error ("octave_calc_anova2: %s", errmsg);
  endif

  ## The analysis, and the comparisons of each factor's levels
  [~, tbl, stats] = anovan (y, groups, 'model', MODEL, 'varnames', names, ...
                            'display', 'off');
  errordf = tbl{strcmp(tbl(:,1), 'Error'), 3};
  if (errordf == 0)
    error (strcat ("octave_calc_anova2: every combination of %s and %s", ...
                   " holds at most one value, so the interaction cannot be", ...
                   " told apart from the error; take the two effects as", ...
                   " adding instead."), names{1}, names{2});
  endif
  comparisons = cell (0, 8);
  for ii = 1:2
    [heading, pairs, errmsg] = octave_calc_pairs (stats, levels{ii}, ...
                                                  CTYPE, ALPHA, ii);
    if (! isempty (errmsg))
      error ("octave_calc_anova2: %s", errmsg);
    endif
    comparisons = [comparisons; pad(); ...
                   pad(sprintf ("%s of %s", heading, names{ii})); ...
                   pad(names{ii}, names{ii}, 'Lower bound', ...
                       'Mean difference', 'Upper bound', 'Statistic', ...
                       'DoF', 'Adjusted p-value'); pairs];
  endfor

  ## The cells, eight columns wide.  The table is built rather than passed
  ## through, anovan's being nine columns wide and naming them its own way
  C = [pad('Two-way ANOVA'); pad(); singular(tbl); ...
       pad(names{1}, names{2}, 'Count', 'Mean', 'Standard deviation'); ...
       cells(y, groups, levels); pad(); ...
       pad('Source', 'SS', 'DoF', 'MS', 'F', 'Prob>F', 'Eta squared', ...
           'Partial eta squared'); ...
       [tbl(2:end,[1, 2, 3, 5, 6, 7, 8, 9])]; comparisons];

endfunction

## One row per combination of the two factors that holds a value
function T = cells (y, groups, levels)
  [ia, ~] = grp2idx (groups{1});
  [ib, ~] = grp2idx (groups{2});
  T = cell (0, 8);
  for aa = 1:numel (levels{1})
    for bb = 1:numel (levels{2})
      here = ia == aa & ib == bb;
      if (! any (here))
        continue;
      endif
      T = [T; pad(levels{1}{aa}, levels{2}{bb}, sum (here), ...
                  mean (y(here)), std (y(here)))];
    endfor
  endfor
endfunction

## A term the fit could not separate is worth saying, since the table it is
## read from does not travel with the results
function R = singular (tbl)
  R = cell (0, 8);
  flags = tbl(2:end,4);
  named = cellfun (@(v) isnumeric (v) && isscalar (v) && v != 0, flags);
  if (! any (named))
    return;
  endif
  R = cell (2, 8);
  terms = strjoin (tbl(find (named) + 1, 1)', ", ");
  R{1,1} = sprintf ("The fit could not separate %s from the rest.", terms);
endfunction

## A row of eight cells, starting with the values given
function R = pad (varargin)
  R = cell (1, 8);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C, D, tbl
%! y = [52; 60; 63; 71; 55; 62; 66; 74; 50; 58; 61; 69; 53; 61; 64; 72];
%! a = {'lo'; 'lo'; 'hi'; 'hi'; 'lo'; 'lo'; 'hi'; 'hi'; ...
%!      'lo'; 'lo'; 'hi'; 'hi'; 'lo'; 'lo'; 'hi'; 'hi'};
%! b = {'x'; 'y'; 'x'; 'y'; 'x'; 'y'; 'x'; 'y'; ...
%!      'x'; 'y'; 'x'; 'y'; 'x'; 'y'; 'x'; 'y'};
%! D = [num2cell(y), a, b];
%! [~, tbl] = anovan (y, {a, b}, 'model', 'interaction', ...
%!                    'varnames', {'Fert', 'Var'}, 'display', 'off');
%! C = octave_calc_anova2 (D, 'labels', {'Fert', 'Var'});
%!test
%! assert_equal (columns (C), 8);
%!test
%! assert_equal (C(1,1), {'Two-way ANOVA'});
%!test
%! assert_equal (C(3,:), {'Fert', 'Var', 'Count', 'Mean', ...
%!                        'Standard deviation', [], [], []});
%!test
%! ## Four combinations, each measured four times
%! assert_equal (C(4:7,3), {4; 4; 4; 4});
%!test
%! assert_equal (C(4,1:2), {'lo', 'x'});
%!test
%! assert_equal (C{4,4}, mean ([52; 55; 50; 53]));
%!test
%! assert_equal (C(9,:), {'Source', 'SS', 'DoF', 'MS', 'F', 'Prob>F', ...
%!                        'Eta squared', 'Partial eta squared'});
%!test
%! assert_equal (C(10:14,1), {'Fert'; 'Var'; 'Fert:Var'; 'Error'; 'Total'});
%!test
%! assert_equal (C(10,2:3), tbl(2,2:3));
%!test
%! ## The Singular? column anovan returns is not written through
%! assert_equal (C(10,4:6), tbl(2,[5, 6, 7]));

%!test
%! ## Each factor gets its own comparisons, named after it
%! assert_equal (C(16,1), {'Multiple comparisons (holm, alpha 0.05) of Fert'});
%!test
%! assert_equal (C(17,1:2), {'Fert', 'Fert'});
%!test
%! assert_equal (C(18,1:2), {'lo', 'hi'});
%!test
%! assert_equal (C(20,1), {'Multiple comparisons (holm, alpha 0.05) of Var'});
%!test
%! assert_equal (C(22,1:2), {'x', 'y'});

%!test
%! ## The values may come after the two factors, reversed before Octave sees
%! ## them, so the wrapper always reads them first
%! R = octave_calc_anova2 (D, 'labels');
%! assert_equal (R(3,1:2), {'Factor 1', 'Factor 2'});

%!test
%! R = octave_calc_anova2 (D, 'labels', {'Fert', 'Var'}, 'linear');
%! assert_equal (R(10:13,1), {'Fert'; 'Var'; 'Error'; 'Total'});

%!test
%! R = octave_calc_anova2 (D, 'labels', {'Fert', 'Var'}, 'interaction', ...
%!                           'bonferroni', 0.01);
%! s = 'Multiple comparisons (bonferroni, alpha 0.01) of Fert';
%! assert_equal (R(16,1), {s});

%!test
%! ## A missing value drops that row and the count of its combination says so
%! E = D;
%! E{1,1} = [];
%! R = octave_calc_anova2 (E, 'labels', {'Fert', 'Var'});
%! here = strcmp (R(4:7,1), 'lo') & strcmp (R(4:7,2), 'x');
%! assert_equal (R{find (here) + 3, 3}, 3);
%!test
%! ## Levels are numbered as they first appear, so dropping the first value
%! ## of a combination can move that combination in the list
%! E = D;
%! E{1,1} = [];
%! R = octave_calc_anova2 (E, 'labels', {'Fert', 'Var'});
%! assert_equal (R(4,1:2), {'lo', 'y'});

%!test
%! ## The interaction needs a combination measured more than once
%! S = {52, 'lo', 'x'; 60, 'lo', 'y'; 63, 'hi', 'x'; 71, 'hi', 'y'};
%! R = octave_calc_anova2 (S, 'labels', {'Fert', 'Var'}, 'linear');
%! assert_equal (R(10:12,1), {'Fert'; 'Var'; 'Error'});

%!error<octave_calc_anova2: invalid number of input arguments.> ...
%! octave_calc_anova2 ({1, 'a', 'b'})
%!error<octave_calc_anova2: MODEL must be 'interaction' or 'linear'.> ...
%! octave_calc_anova2 ({1, 'a', 'b'; 2, 'c', 'd'}, 'labels', [], 'full')
%!error<octave_calc_anova2: BY must be 'labels'.> ...
%! octave_calc_anova2 ({1, 'a', 'b'}, 'columns')
%!error<octave_calc_anova2: DATA must have three columns, the values and the two factors of each.> ...
%! octave_calc_anova2 ({1, 'a'; 2, 'b'}, 'labels')
%!error<octave_calc_anova2: Factor 1 holds fewer than two levels.> ...
%! octave_calc_anova2 ({1, 'a', 'x'; 2, 'a', 'y'}, 'labels')
%!error<octave_calc_anova2: the input range holds a value with no Factor 2.> ...
%! octave_calc_anova2 ({1, 'a', 'x'; 2, 'b', ''}, 'labels')
%!error<octave_calc_anova2: both factors carry the name 'A'.> ...
%! octave_calc_anova2 ({1, 'a', 'x'; 2, 'b', 'y'}, 'labels', {'A', 'A'})
%!error<octave_calc_anova2: every combination of Fert and Var holds at most one value, so the interaction cannot be told apart from the error; take the two effects as adding instead.> ...
%! octave_calc_anova2 ({52, 'lo', 'x'; 60, 'lo', 'y'; 63, 'hi', 'x'; ...
%!                      71, 'hi', 'y'}, 'labels', {'Fert', 'Var'})
%!error<octave_calc_anova2: every combination of Factor 1 and Factor 2 holds at most one value,> ...
%! octave_calc_anova2 ({52, 'lo', 'x'; 60, 'lo', 'y'; 63, 'hi', 'x'; ...
%!                      71, 'hi', 'y'}, 'labels')
