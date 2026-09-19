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
## @deftypefn {octave-calc} {[@var{X}, @var{labels}, @var{dropped}, @var{errmsg}] =} octave_calc_matched (@var{DATA}, @var{BY}, @var{NAMES})
##
## The matched measurements an input range holds, for the analyses of Data >
## Statistics with GNU Octave.
##
## @var{DATA} is the input range and @var{BY} says how it holds the
## measurements: @qcode{'columns'}, one per column and a subject per row, or
## @qcode{'rows'}, one per row and a subject per column.  @var{NAMES} names
## them where it names them, and their place names the rest.
##
## @var{X} holds one subject per row and one measurement per column.  A
## subject missing any of its measurements takes part in none of them, since
## the measurements are compared with each other and a subject that has only
## some would weigh into one side and not the other; @var{dropped} counts the
## subjects left out that way, for the analysis to report.
##
## @var{errmsg} is the body of an error message when the range cannot be read
## that way, and the caller raises it under its own name; @var{X} is then
## empty.
##
## @end deftypefn

function [X, labels, dropped, errmsg] = octave_calc_matched (DATA, BY, NAMES)

  X = [];
  labels = cell (0, 1);
  dropped = 0;
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
    stem = 'Row';
  else
    stem = 'Column';
  endif
  k = columns (DATA);
  labels = arrayfun (@(ii) sprintf ("%s %d", stem, ii), (1:k)', ...
                     "UniformOutput", false);
  if (! isempty (NAMES))
    [names, errmsg] = octave_calc_names (NAMES, "NAMES");
    if (! isempty (errmsg))
      labels = cell (0, 1);
      return;
    endif
    if (numel (names) != k)
      errmsg = "NAMES must hold one name for each measurement.";
      labels = cell (0, 1);
      return;
    endif
    given = ! cellfun (@isempty, names);
    labels(given) = names(given);
    [~, first] = unique (labels, "first");
    if (numel (first) < k)
      errmsg = sprintf ("two measurements share the name '%s'.", ...
                        labels{setdiff(1:k, first)(1)});
      labels = cell (0, 1);
      return;
    endif
  endif
  if (k < 2)
    errmsg = "the input range holds fewer than two measurements.";
    labels = cell (0, 1);
    return;
  endif

  complete = ! any (isnan (DATA), 2);
  dropped = sum (! complete);
  X = DATA(complete,:);
  if (rows (X) < 2)
    X = [];
    labels = cell (0, 1);
    dropped = 0;
    errmsg = strcat ("fewer than two subjects hold every measurement;", ...
                     " there is nothing to compare.");
  endif

endfunction
