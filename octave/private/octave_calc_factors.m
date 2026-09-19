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
## @deftypefn {octave-calc} {[@var{y}, @var{groups}, @var{levels}, @var{names}, @var{errmsg}] =} octave_calc_factors (@var{DATA}, @var{BY}, @var{NAMES})
##
## The two factors an input range holds, for the analyses of Data >
## Statistics with GNU Octave.
##
## @var{DATA} is the input range, three columns wide: each value and the two
## factors it was measured under.  @var{BY} must be @qcode{'labels'}, the
## values having been put first before Octave sees them.  @var{NAMES} names
## the two factors, and they are @qcode{'Factor 1'} and @qcode{'Factor 2'}
## otherwise.  @code{NaN} stands for an empty cell and is left out.
##
## @var{y} holds every value in one column and @var{groups} is a cell of two
## columns of labels, one per factor, as @code{anovan} takes them.
## @var{levels} is a cell of two columns, the levels of each factor in the
## order they are numbered: numeric levels from the smallest, and, where any
## level is text, in the order they first appear.
##
## @var{errmsg} is the body of an error message when the range cannot be read
## that way, and the caller raises it under its own name; @var{y} is then
## empty.
##
## @end deftypefn

function [y, groups, levels, names, errmsg] = octave_calc_factors (DATA, ...
                                                                   BY, NAMES)

  y = [];
  groups = cell (1, 2);
  levels = cell (1, 2);
  names = {'Factor 1', 'Factor 2'};
  errmsg = "";

  if (nargin != 3)
    errmsg = "invalid number of input arguments.";
    return;
  endif
  if (! (ischar (BY) && strcmp (BY, 'labels')))
    errmsg = "BY must be 'labels'.";
    return;
  endif
  if (! (ismatrix (DATA) && columns (DATA) == 3
         && ((isnumeric (DATA) && isreal (DATA)) || iscell (DATA))))
    errmsg = strcat ("DATA must have three columns, the values and the", ...
                     " two factors of each.");
    return;
  endif

  ## The names of the two factors, where the header gave them
  if (! isempty (NAMES))
    [given, errmsg] = octave_calc_names (NAMES, "NAMES");
    if (! isempty (errmsg))
      return;
    endif
    if (numel (given) != 2)
      errmsg = "NAMES must hold one name for each of the two factors.";
      return;
    endif
    held = ! cellfun (@isempty, given);
    names(held) = given(held);
    if (strcmp (names{1}, names{2}))
      errmsg = sprintf ("both factors carry the name '%s'.", names{1});
      return;
    endif
  endif

  ## The values, an empty cell standing for a missing one
  if (isnumeric (DATA))
    y = DATA(:,1);
  else
    number = @(v) isnumeric (v) && isreal (v) && isscalar (v);
    if (! all (cellfun (@(v) number (v) || isempty (v), DATA(:,1))))
      errmsg = "the values in DATA must be numbers.";
      return;
    endif
    y = nan (rows (DATA), 1);
    present = ! cellfun (@isempty, DATA(:,1));
    y(present) = [DATA{present,1}];
  endif
  keep = ! isnan (y);

  ## The levels of each factor beside the values that are there
  for ii = 1:2
    if (isnumeric (DATA))
      labels = DATA(keep,ii + 1);
      missing = isnan (labels);
    else
      [labels, errmsg] = octave_calc_names (DATA(keep,ii + 1), ...
                                            sprintf ("the labels of %s", ...
                                                     names{ii}));
      if (! isempty (errmsg))
        y = [];
        return;
      endif
      missing = cellfun (@isempty, labels);
    endif
    if (any (missing))
      y = [];
      errmsg = sprintf ("the input range holds a value with no %s.", ...
                        names{ii});
      return;
    endif
    [index, these] = grp2idx (labels);
    groups{ii} = labels;
    levels{ii} = these(:);
    if (numel (these) < 2)
      y = [];
      errmsg = sprintf ("%s holds fewer than two levels.", names{ii});
      return;
    endif
  endfor
  y = y(keep);

endfunction
