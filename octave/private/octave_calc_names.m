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
## @deftypefn {octave-calc} {[@var{names}, @var{errmsg}] =} octave_calc_names (@var{V}, @var{WHAT})
##
## The names a header row or column holds, for the analyses of Data >
## Statistics with GNU Octave.
##
## @var{V} is a numeric vector, or a cell array of text, numbers and empty
## values, as the header of an input range reaches Octave.  @var{names} is a
## column of text with one entry for each, a number written out and a missing
## name left as empty text.
##
## @var{errmsg} is the body of an error message when @var{V} holds anything
## else, naming it @var{WHAT}, and the caller raises it under its own name;
## @var{names} is then empty.
##
## @end deftypefn

function [names, errmsg] = octave_calc_names (V, WHAT)

  names = cell (0, 1);
  errmsg = "";

  if (isnumeric (V) && isreal (V))
    V = num2cell (V);
  endif
  isname = @(v) (isnumeric (v) && isreal (v) && isscalar (v)) || isempty (v) ...
                || (ischar (v) && rows (v) <= 1);
  if (! (iscell (V) && all (cellfun (isname, V(:)))))
    errmsg = sprintf ("%s must be text or numbers.", WHAT);
    return;
  endif
  names = cell (numel (V), 1);
  for ii = 1:numel (V)
    v = V{ii};
    if (ischar (v))
      names{ii} = v;
    elseif (! (isempty (v) || isnan (v)))
      names{ii} = num2str (v);
    else
      names{ii} = '';
    endif
  endfor

endfunction
