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
## @deftypefn {octave-calc} {[@var{x}, @var{label}, @var{errmsg}] =} octave_calc_sample (@var{DATA}, @var{BY}, @var{NAMES})
##
## The one sample an input range holds, for the analyses of Data > Statistics
## with GNU Octave.
##
## @var{DATA} is the input range and @var{BY} says how it holds the sample:
## @qcode{'columns'}, one column of values, or @qcode{'rows'}, one row of
## them.  @var{NAMES} names it, and it is @qcode{'Sample'} otherwise.
## @code{NaN} stands for an empty cell and is left out.
##
## @var{x} holds the values in one column and @var{label} is the sample's
## name.
##
## @var{errmsg} is the body of an error message when the range cannot be read
## that way, and the caller raises it under its own name; @var{x} is then
## empty.
##
## @end deftypefn

function [x, label, errmsg] = octave_calc_sample (DATA, BY, NAMES)

  x = [];
  label = 'Sample';
  errmsg = "";

  if (nargin != 3)
    errmsg = "invalid number of input arguments.";
    return;
  endif
  if (! (ischar (BY) && any (strcmp (BY, {'columns', 'rows'}))))
    errmsg = "BY must be 'columns' or 'rows'.";
    return;
  endif
  if (! (isnumeric (DATA) && isreal (DATA) && ismatrix (DATA)))
    errmsg = "DATA must be a real numeric matrix.";
    return;
  endif

  if (strcmp (BY, 'rows'))
    DATA = DATA.';
    what = 'one row';
  else
    what = 'one column';
  endif
  if (columns (DATA) != 1)
    errmsg = sprintf ("the input range must hold %s of values.", what);
    return;
  endif

  if (! isempty (NAMES))
    [given, errmsg] = octave_calc_names (NAMES, "NAMES");
    if (! isempty (errmsg))
      return;
    endif
    if (numel (given) != 1)
      errmsg = "NAMES must hold one name for the sample.";
      return;
    endif
    if (! isempty (given{1}))
      label = given{1};
    endif
  endif

  x = DATA(! isnan (DATA));
  if (numel (x) < 2)
    x = [];
    errmsg = "the sample holds fewer than two numbers.";
  endif

endfunction
