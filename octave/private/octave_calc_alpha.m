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
## @deftypefn {octave-calc} {@var{errmsg} =} octave_calc_alpha (@var{ALPHA})
##
## Whether a significance level is one, for the analyses of Data > Statistics
## with GNU Octave.
##
## @var{errmsg} is the body of an error message when @var{ALPHA} is not a
## number greater than 0 and less than 1, and the caller raises it under its
## own name; it is empty otherwise.
##
## @end deftypefn

function errmsg = octave_calc_alpha (ALPHA)

  errmsg = "";

  if (nargin != 1)
    errmsg = "invalid number of input arguments.";
    return;
  endif
  if (! (isnumeric (ALPHA) && isreal (ALPHA) && isscalar (ALPHA)
         && ALPHA > 0 && ALPHA < 1))
    errmsg = "ALPHA must be a number greater than 0 and less than 1.";
  endif

endfunction
