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
## @deftypefn {octave-calc} {[@var{x}, @var{group}, @var{labels}, @var{errmsg}] =} octave_calc_groups (@var{DATA}, @var{BY}, @var{NAMES})
##
## The groups an input range holds, for the analyses of Data > Statistics with
## GNU Octave.
##
## @var{DATA} is the input range and @var{BY} says how it holds the groups:
## @qcode{'columns'} or @qcode{'rows'}, one group each, named after
## @var{NAMES} where it names them and after their place otherwise; or
## @qcode{'labels'}, two columns, each value beside the label of its group,
## which @var{NAMES} may not accompany.  @code{NaN} stands for an empty cell
## and is left out.
##
## @var{x} holds every value in one column, @var{group} the number of its
## group, and @var{labels} the name of each group.  Numeric labels are ordered
## from the smallest; when any label is text, the groups are ordered as they
## first appear.
##
## @var{errmsg} is the body of an error message when the range cannot be read
## that way, and the caller raises it under its own name; @var{x} is then
## empty.
##
## @end deftypefn

function [x, group, labels, errmsg] = octave_calc_groups (DATA, BY, NAMES)

  x = [];
  group = [];
  labels = cell (0, 1);
  errmsg = "";

  if (nargin != 3)
    errmsg = "invalid number of input arguments.";
    return;
  endif
  if (! (ischar (BY) && any (strcmp (BY, {'columns', 'rows', 'labels'}))))
    errmsg = "BY must be 'columns', 'rows' or 'labels'.";
    return;
  endif

  if (strcmp (BY, 'labels'))
    if (! isempty (NAMES))
      errmsg = "NAMES applies only to groups in columns or rows.";
      return;
    endif
    [x, group, labels, errmsg] = labelled (DATA);
  else
    [x, group, labels, errmsg] = samples (DATA, BY, NAMES);
  endif
  if (! isempty (errmsg))
    return;
  endif
  if (numel (labels) < 2)
    errmsg = "the input range holds fewer than two groups.";
  endif

endfunction

## Every value in one column, beside the number of its group, from one group
## per column or per row, named after NAMES where it names them
function [x, group, labels, errmsg] = samples (DATA, BY, NAMES)
  x = [];
  group = [];
  labels = cell (0, 1);
  errmsg = "";
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
    [names, errmsg] = texts (NAMES, "NAMES");
    if (! isempty (errmsg))
      return;
    endif
    if (numel (names) != k)
      errmsg = "NAMES must hold one name for each group.";
      return;
    endif
    given = ! cellfun (@isempty, names);
    labels(given) = names(given);
    [~, first] = unique (labels, "first");
    if (numel (first) < k)
      errmsg = sprintf ("two groups share the name '%s'.", ...
                        labels{setdiff(1:k, first)(1)});
      return;
    endif
  endif
  for ii = 1:k
    values = DATA(! isnan (DATA(:,ii)), ii);
    if (isempty (values) && k > 1)
      errmsg = sprintf ("the group '%s' holds no numbers.", labels{ii});
      return;
    endif
    x = [x; values];
    group = [group; repmat(ii, numel (values), 1)];
  endfor
endfunction

## Every value in one column, beside the number of its group, from values
## beside their group labels
function [x, group, labels, errmsg] = labelled (DATA)
  x = [];
  group = [];
  labels = cell (0, 1);
  errmsg = "";
  if (! (ismatrix (DATA) && columns (DATA) == 2
         && ((isnumeric (DATA) && isreal (DATA)) || iscell (DATA))))
    errmsg = "DATA must have two columns, the values and their group labels.";
    return;
  endif
  if (isnumeric (DATA))
    x = DATA(:,1);
  else
    number = @(v) isnumeric (v) && isreal (v) && isscalar (v);
    if (! all (cellfun (@(v) number (v) || isempty (v), DATA(:,1))))
      errmsg = "the values in DATA must be numbers.";
      return;
    endif
    x = nan (rows (DATA), 1);
    present = ! cellfun (@isempty, DATA(:,1));
    x(present) = [DATA{present,1}];
  endif
  keep = ! isnan (x);
  if (isnumeric (DATA))
    names = DATA(keep,2);
    missing = isnan (names);
  else
    [names, errmsg] = texts (DATA(keep,2), "the group labels in DATA");
    if (! isempty (errmsg))
      x = [];
      return;
    endif
    missing = cellfun (@isempty, names);
  endif
  if (any (missing))
    x = [];
    errmsg = "the input range holds a value with no group label.";
    return;
  endif
  x = x(keep);
  if (! isempty (x))
    [group, labels] = grp2idx (names);
  endif
endfunction

## Names as a column of text, from a numeric vector or a cell array of text,
## numbers and empty values; a missing name is empty text
function [names, errmsg] = texts (V, what)
  names = cell (0, 1);
  errmsg = "";
  if (isnumeric (V) && isreal (V))
    V = num2cell (V);
  endif
  isname = @(v) (isnumeric (v) && isreal (v) && isscalar (v)) || isempty (v) ...
                || (ischar (v) && rows (v) <= 1);
  if (! (iscell (V) && all (cellfun (isname, V(:)))))
    errmsg = sprintf ("%s must be text or numbers.", what);
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
