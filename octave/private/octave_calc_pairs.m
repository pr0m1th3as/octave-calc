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
## @deftypefn {octave-calc} {[@var{heading}, @var{pairs}, @var{errmsg}] =} octave_calc_pairs (@var{STATS}, @var{LABELS}, @var{CTYPE}, @var{ALPHA})
##
## The pairwise comparisons that follow a test, for the analyses of Data >
## Statistics with GNU Octave.
##
## @var{STATS} is what the test returned as its third output and @var{LABELS}
## the name of each group.  @var{CTYPE} is how @code{multcompare} adjusts the
## p-values, one of @qcode{'bonferroni'}, @qcode{'scheffe'}, @qcode{'mvt'},
## @qcode{'holm'}, @qcode{'hochberg'}, @qcode{'fdr'} or @qcode{'lsd'}, and
## @var{ALPHA} the significance level, greater than 0 and less than 1, which
## also sets the confidence intervals.
##
## @var{heading} names both above the comparisons, and @var{pairs} is a cell
## array of one row per pair of groups, eight columns wide: the two groups,
## then the lower bound, the estimate and the upper bound of their difference,
## the test statistic, its degrees of freedom, and the adjusted p-value, which
## comes last as it does in an ANOVA table.  Degrees of freedom of @code{Inf}
## are kept, since they say the statistic is a z, and the sheet holds them as
## the text @qcode{'Inf'}, which reads back as a number where an empty cell
## would read back as @code{NaN}.
##
## @var{errmsg} is the body of an error message when @var{CTYPE} or
## @var{ALPHA} is not one of those, and the caller raises it under its own
## name; @var{pairs} is then empty.
##
## @end deftypefn

function [heading, pairs, errmsg] = octave_calc_pairs (STATS, LABELS, ...
                                                       CTYPE, ALPHA)

  heading = "";
  pairs = cell (0, 8);
  errmsg = "";

  if (nargin != 4)
    errmsg = "invalid number of input arguments.";
    return;
  endif
  ctypes = {'bonferroni', 'scheffe', 'mvt', 'holm', 'hochberg', 'fdr', 'lsd'};
  if (! (ischar (CTYPE) && any (strcmp (CTYPE, ctypes))))
    errmsg = strcat ("CTYPE must be 'bonferroni', 'scheffe', 'mvt',", ...
                     " 'holm', 'hochberg', 'fdr' or 'lsd'.");
    return;
  endif
  if (! (isnumeric (ALPHA) && isreal (ALPHA) && isscalar (ALPHA)
         && ALPHA > 0 && ALPHA < 1))
    errmsg = "ALPHA must be a number greater than 0 and less than 1.";
    return;
  endif

  c = multcompare (STATS, 'ctype', CTYPE, 'alpha', ALPHA, 'display', 'off');
  heading = sprintf ("Multiple comparisons (%s, alpha %g)", CTYPE, ALPHA);
  pairs = [LABELS(c(:,1)), LABELS(c(:,2)), num2cell(c(:,[3, 4, 5, 7, 8, 6]))];

endfunction
