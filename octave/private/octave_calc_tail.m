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
## @deftypefn {octave-calc} {[@var{word}, @var{errmsg}] =} octave_calc_tail (@var{TAIL})
##
## How a test's heading names its alternative hypothesis, for the analyses of
## Data > Statistics with GNU Octave.
##
## @var{TAIL} is @qcode{'both'}, @qcode{'right'} or @qcode{'left'}, as the
## @code{statistics} tests take it, and @var{word} is
## @qcode{'two-sided'}, @qcode{'right-sided'} or @qcode{'left-sided'}.
##
## @var{errmsg} is the body of an error message when @var{TAIL} is not one of
## those, and the caller raises it under its own name; @var{word} is then
## empty.
##
## @end deftypefn

function [word, errmsg] = octave_calc_tail (TAIL)

  word = "";
  errmsg = "";

  if (nargin != 1)
    errmsg = "invalid number of input arguments.";
    return;
  endif
  tails = {'both', 'right', 'left'};
  if (! (ischar (TAIL) && any (strcmp (TAIL, tails))))
    errmsg = "TAIL must be 'both', 'right' or 'left'.";
    return;
  endif

  switch (TAIL)
    case 'both'
      word = 'two-sided';
    case 'right'
      word = 'right-sided';
    case 'left'
      word = 'left-sided';
  endswitch

endfunction
