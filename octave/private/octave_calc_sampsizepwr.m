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
## @deftypefn {octave-calc} {[@var{C}, @var{errmsg}] =} octave_calc_sampsizepwr (@var{WANT}, @var{TESTTYPE}, @var{NULLVALUE}, @var{NULLSD}, @var{P1}, @var{POWER}, @var{N}, @var{ALPHA})
##
## Sample size, power or detectable difference, for the analyses of Data >
## Statistics with GNU Octave.
##
## @var{WANT} is what @code{sampsizepwr} is to compute, @qcode{'n'},
## @qcode{'power'} or @qcode{'p1'}, and the matching input is ignored.
## @var{TESTTYPE} is @qcode{'z'}, @qcode{'t'}, @qcode{'t2'}, @qcode{'var'},
## @qcode{'p'} or @qcode{'r'}.  @var{NULLVALUE} is the parameter under the null
## hypothesis and @var{NULLSD} the standard deviation beside it, which
## @qcode{'z'}, @qcode{'t'} and @qcode{'t2'} take and the others ignore.
## @var{P1} is the parameter under the alternative hypothesis, @var{N} the
## sample size, @var{POWER} the power, and @var{ALPHA} the significance level.
##
## @var{C} is a cell array two columns wide, laid out as the cells written into
## the sheet: what was given, then what was computed.  @var{errmsg} is the body
## of an error message when the inputs do not answer the question, and the
## caller raises it under its own name; @var{C} is then empty.
##
## @end deftypefn

function [C, errmsg] = octave_calc_sampsizepwr (WANT, TESTTYPE, NULLVALUE, ...
                                                NULLSD, P1, POWER, N, ALPHA)

  C = cell (0, 2);
  errmsg = "";

  if (nargin != 8)
    errmsg = "invalid number of input arguments.";
    return;
  endif
  types = {'z', 't', 't2', 'var', 'p', 'r'};
  if (! (ischar (TESTTYPE) && any (strcmp (TESTTYPE, types))))
    errmsg = strcat ("TESTTYPE must be 'z', 't', 't2', 'var', 'p'", ...
                     " or 'r'.");
    return;
  endif
  if (! number (NULLVALUE))
    errmsg = "the null value must be a number.";
    return;
  endif
  paired = any (strcmp (TESTTYPE, {'z', 't', 't2'}));
  if (paired && ! (number (NULLSD) && NULLSD > 0))
    errmsg = "the null standard deviation must be a number greater than 0.";
    return;
  endif
  if (! (number (ALPHA) && ALPHA > 0 && ALPHA < 1))
    errmsg = strcat ("the significance level must be a number greater", ...
                     " than 0 and less than 1.");
    return;
  endif
  if (! strcmp (WANT, 'p1') && ! number (P1))
    errmsg = "the alternative value must be a number.";
    return;
  endif
  if (! strcmp (WANT, 'power') && ! (number (POWER) && POWER > 0 && POWER < 1))
    errmsg = "the power must be a number greater than 0 and less than 1.";
    return;
  endif
  if (! strcmp (WANT, 'n') && ! (number (N) && N == fix (N) && N > 1))
    errmsg = "the sample size must be a whole number of 2 or more.";
    return;
  endif

  ## What sampsizepwr is asked, the wanted one left empty
  if (paired)
    params = [NULLVALUE, NULLSD];
  else
    params = NULLVALUE;
  endif
  switch (WANT)
    case 'n'
      P1n = P1;
      POWERn = POWER;
      Nn = [];
    case 'power'
      P1n = P1;
      POWERn = [];
      Nn = N;
    otherwise
      P1n = [];
      POWERn = POWER;
      Nn = N;
  endswitch

  try
    if (strcmp (WANT, 'n') && strcmp (TESTTYPE, 't2'))
      [first, second] = sampsizepwr (TESTTYPE, params, P1n, POWERn, Nn, ...
                                     'alpha', ALPHA);
      answer = [first, second];
    else
      answer = sampsizepwr (TESTTYPE, params, P1n, POWERn, Nn, ...
                            'alpha', ALPHA);
    endif
  catch err
    errmsg = strrep (err.message, "sampsizepwr: ", "");
    return;
  end_try_catch

  ## The cells, two columns wide
  C = {'Test', testname(TESTTYPE); 'Null value', NULLVALUE};
  if (paired)
    C = [C; {'Null standard deviation', NULLSD}];
  endif
  if (! strcmp (WANT, 'p1'))
    C = [C; {'Alternative value', P1}];
  endif
  if (! strcmp (WANT, 'power'))
    C = [C; {'Power', POWER}];
  endif
  if (! strcmp (WANT, 'n'))
    C = [C; {'Sample size', N}];
  endif
  C = [C; {'Significance level', ALPHA}; cell(1, 2)];
  switch (WANT)
    case 'n'
      if (strcmp (TESTTYPE, 't2'))
        C = [C; {'Sample size, first group', answer(1); ...
                 'Sample size, second group', answer(2)}];
      else
        C = [C; {'Sample size', answer}];
      endif
    case 'power'
      C = [C; {'Power', answer}];
    otherwise
      C = [C; {'Alternative value', answer}];
  endswitch

endfunction

## A real numeric scalar
function tf = number (v)
  tf = isnumeric (v) && isreal (v) && isscalar (v) && ! isnan (v);
endfunction

## What a test type is called in the sheet
function name = testname (TESTTYPE)
  switch (TESTTYPE)
    case 'z'
      name = 'one-sample z-test';
    case 't'
      name = 'one-sample or paired t-test';
    case 't2'
      name = 'two-sample t-test';
    case 'var'
      name = 'chi-square test of a variance';
    case 'p'
      name = 'test of a proportion';
    otherwise
      name = 'test of a correlation';
  endswitch
endfunction
