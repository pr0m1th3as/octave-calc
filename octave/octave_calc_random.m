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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_random (@var{DISTNAME}, @var{NROWS}, @var{NCOLS}, @var{SEED})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_random (@var{DISTNAME}, @var{NROWS}, @var{NCOLS}, @var{SEED}, @var{P1}, @dots{})
##
## Random numbers for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_random (@var{DISTNAME}, @var{NROWS},
## @var{NCOLS}, @var{SEED}, @var{P1}, @dots{})} draws @var{NROWS} by
## @var{NCOLS} values from the distribution @var{DISTNAME}, whose parameters
## follow the seed one number each, in the order @code{makedist} names them.
##
## @var{SEED} seeds the generators before the draw, so that the same seed
## draws the same numbers again.  Where it is empty a seed is chosen from the
## clock.
##
## Every generator with a state of its own is seeded, not @code{rand} and
## @code{randn} alone: a Poisson draw goes through @code{randp} and a gamma
## draw through @code{randg}, and seeding the first two leaves both of those
## free to wander.
##
## @var{C} is a cell array of the drawn numbers, @var{NROWS} by
## @var{NCOLS}, and holds nothing else: no title, no heading and no note of
## what drew them.  It is written into the cells the user chose, and they
## hold numbers as any other cells do.
##
## The draw is capped at 100,000 numbers, since the results are written to
## the sheet one cell at a time.
##
## The @code{statistics} package must be loaded.
##
## @seealso{makedist, random}
## @end deftypefn

function C = octave_calc_random (DISTNAME, NROWS, NCOLS, SEED, varargin)

  ## Input validation
  if (nargin < 4)
    error ("octave_calc_random: invalid number of input arguments.");
  endif
  if (! (ischar (DISTNAME) && any (strcmpi (DISTNAME, makedist ()))))
    error (strcat ("octave_calc_random: DISTNAME must be a distribution", ...
                   " makedist takes."));
  endif
  PARAMS = [varargin{:}];
  if (! (isnumeric (PARAMS) && isreal (PARAMS)
         && numel (PARAMS) == numel (varargin)))
    error ("octave_calc_random: each parameter must be one number.");
  endif
  [nrows, errmsg] = counted (NROWS, "NROWS");
  if (! isempty (errmsg))
    error ("octave_calc_random: %s", errmsg);
  endif
  [ncols, errmsg] = counted (NCOLS, "NCOLS");
  if (! isempty (errmsg))
    error ("octave_calc_random: %s", errmsg);
  endif
  if (nrows * ncols > 100000)
    error (strcat ("octave_calc_random: %d by %d is %d numbers and the", ...
                   " most that can be written is 100000."), nrows, ncols, ...
           nrows * ncols);
  endif
  if (! (isempty (SEED) || (isnumeric (SEED) && isreal (SEED)
                            && isscalar (SEED) && SEED == fix (SEED)
                            && SEED >= 0)))
    error (strcat ("octave_calc_random: SEED must be a whole number of 0", ...
                   " or more, or nothing at all."));
  endif

  ## The distribution, its parameters paired with the names makedist gives
  ## them so that neither side has to assume an order
  names = makedist (DISTNAME).ParameterNames;
  if (numel (PARAMS) != numel (names))
    ending = "s";
    if (numel (names) == 1)
      ending = "";
    endif
    given = "were";
    if (numel (PARAMS) == 1)
      given = "was";
    endif
    error (strcat ("octave_calc_random: %s takes %d parameter%s, %s,", ...
                   " and %d %s given."), DISTNAME, numel (names), ending, ...
           strjoin (names, ", "), numel (PARAMS), given);
  endif
  pairs = cell (1, 2 * numel (names));
  pairs(1:2:end) = names;
  pairs(2:2:end) = num2cell (PARAMS(:).');
  try
    pd = makedist (DISTNAME, pairs{:});
  catch err
    error ("octave_calc_random: %s", ...
           strtrim (regexprep (err.message, '^[^:]*:', '')));
  end_try_catch

  ## The draw, under the seed given or one taken from the clock
  if (isempty (SEED))
    SEED = mod (floor (now () * 86400000), 2 ^ 31);
  endif
  for g = {'rand', 'randn', 'randp', 'rande', 'randg'}
    feval (g{1}, 'seed', SEED);
  endfor

  ## The numbers, and nothing besides
  C = num2cell (random (pd, nrows, ncols));

endfunction

## A whole count of one or more
function [n, errmsg] = counted (N, what)
  n = 0;
  errmsg = "";
  if (! (isnumeric (N) && isreal (N) && isscalar (N) && N == fix (N)
         && N >= 1))
    errmsg = sprintf ("%s must be a whole number of 1 or more.", what);
    return;
  endif
  n = N;
endfunction

## A row of WIDTH cells, starting with the values given
function R = pad (width, varargin)
  R = cell (1, width);
  R(1:numel (varargin)) = varargin;
endfunction

%!shared C
%! C = octave_calc_random ('Normal', 3, 4, 7, 5, 2);
%!test
%! ## The draw is the whole of it: the size asked for, and no lines about it
%! assert_equal (size (C), [3, 4]);
%!test
%! assert_equal (all (cellfun (@isnumeric, C(:))), true);
%!test
%! ## The same seed draws the same numbers again
%! R = octave_calc_random ('Normal', 3, 4, 7, 5, 2);
%! assert_equal (C, R);
%!test
%! ## A different seed does not
%! R = octave_calc_random ('Normal', 3, 4, 8, 5, 2);
%! assert_equal (isequal (C, R), false);
%!test
%! ## The parameters reach the draw
%! R = cell2mat (octave_calc_random ('Normal', 1, 2000, 7, 100, 1));
%! assert_equal (abs (mean (R) - 100) < 1, true);

%!test
%! ## One cell is a draw like any other
%! R = octave_calc_random ('Normal', 1, 1, 7, 5, 2);
%! assert_equal (size (R), [1, 1]);
%!test
%! ## and a column
%! R = octave_calc_random ('Normal', 10, 1, 7, 5, 2);
%! assert_equal (size (R), [10, 1]);

%!test
%! ## A seed that was not given is taken from the clock and still draws
%! R = octave_calc_random ('Normal', 2, 2, [], 5, 2);
%! assert_equal (size (R), [2, 2]);
%!test
%! ## An empty seed is what the dialog sends for a seed left blank
%! R = octave_calc_random ('Normal', 2, 2, '', 5, 2);
%! assert_equal (all (cellfun (@isnumeric, R(:))), true);

%!test
%! ## A Poisson draw goes through randp, which rand and randn do not seed
%! R = octave_calc_random ('Poisson', 1, 8, 3, 4);
%! S = octave_calc_random ('Poisson', 1, 8, 3, 4);
%! assert_equal (R, S);
%!test
%! ## and a gamma draw through randg
%! R = octave_calc_random ('Gamma', 1, 8, 3, 2, 3);
%! S = octave_calc_random ('Gamma', 1, 8, 3, 2, 3);
%! assert_equal (R, S);

%!test
%! ## Every parameter reaches the distribution it names
%! R = octave_calc_random ('Stable', 2, 2, 1, 1.5, 0, 1, 0);
%! assert_equal (size (R), [2, 2]);

%!error<octave_calc_random: invalid number of input arguments.> ...
%! octave_calc_random ('Normal', 3, 4)
%!error<octave_calc_random: DISTNAME must be a distribution makedist takes.> ...
%! octave_calc_random ('Gaussian', 3, 4, [], 5, 2)
%!error<octave_calc_random: each parameter must be one number.> ...
%! octave_calc_random ('Normal', 3, 4, [], 'five', 2)
%!error<octave_calc_random: each parameter must be one number.> ...
%! octave_calc_random ('Normal', 3, 4, [], [5, 1], 2)
%!error<octave_calc_random: NROWS must be a whole number of 1 or more.> ...
%! octave_calc_random ('Normal', 0, 4, [], 5, 2)
%!error<octave_calc_random: NCOLS must be a whole number of 1 or more.> ...
%! octave_calc_random ('Normal', 3, 1.5, [], 5, 2)
%!error<octave_calc_random: 1000 by 1000 is 1000000 numbers and the most that can be written is 100000.> ...
%! octave_calc_random ('Normal', 1000, 1000, [], 5, 2)
%!error<octave_calc_random: SEED must be a whole number of 0 or more, or nothing at all.> ...
%! octave_calc_random ('Normal', 3, 4, -1, 5, 2)
%!error<octave_calc_random: Normal takes 2 parameters, mu, sigma, and 1 was given.> ...
%! octave_calc_random ('Normal', 3, 4, [], 5)
%!error<octave_calc_random: Poisson takes 1 parameter, lambda, and 2 were given.> ...
%! octave_calc_random ('Poisson', 3, 4, [], 4, 5)
%!error<octave_calc_random: Poisson takes 1 parameter, lambda, and 0 were given.> ...
%! octave_calc_random ('Poisson', 3, 4, [])
