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
## @deftypefn  {octave-calc} {@var{C} =} octave_calc_random (@var{DISTNAME}, @var{PARAMS}, @var{NROWS}, @var{NCOLS})
## @deftypefnx {octave-calc} {@var{C} =} octave_calc_random (@var{DISTNAME}, @var{PARAMS}, @var{NROWS}, @var{NCOLS}, @var{SEED})
##
## Random numbers for Data > Statistics with GNU Octave.
##
## @code{@var{C} = octave_calc_random (@var{DISTNAME}, @var{PARAMS},
## @var{NROWS}, @var{NCOLS})} draws @var{NROWS} by @var{NCOLS} values from
## the distribution @var{DISTNAME} with the parameters @var{PARAMS}, which
## are a row of numbers, one for each parameter the distribution takes, in
## the order @code{makedist} names them.
##
## @var{SEED} seeds the generators before the draw and is written above the
## numbers.  Where it is empty a seed is chosen from the clock, used, and
## written out just the same, so that a block of numbers always records what
## would produce it again.
##
## Every generator with a state of its own is seeded, not @code{rand} and
## @code{randn} alone: a Poisson draw goes through @code{randp} and a gamma
## draw through @code{randg}, and seeding the first two leaves both of those
## free to wander.
##
## @var{C} is a cell array of scalars, text and empty values, laid out as the
## cells written into the sheet: the title; the distribution, its parameters,
## the size and the seed; then the numbers themselves.  It is as wide as
## @var{NCOLS} or four, whichever is the greater, so that the lines above
## the numbers are never cut short.
##
## The block is capped at 100,000 numbers, since the results are written to
## the sheet one cell at a time.
##
## The @code{statistics} package must be loaded.
##
## @seealso{makedist, random}
## @end deftypefn

function C = octave_calc_random (DISTNAME, PARAMS, NROWS, NCOLS, SEED)

  ## Input validation
  if (nargin < 4 || nargin > 5)
    error ("octave_calc_random: invalid number of input arguments.");
  endif
  if (nargin < 5)
    SEED = [];
  endif
  if (! (ischar (DISTNAME) && any (strcmpi (DISTNAME, makedist ()))))
    error (strcat ("octave_calc_random: DISTNAME must be a distribution", ...
                   " makedist takes."));
  endif
  if (! (isnumeric (PARAMS) && isreal (PARAMS) && isvector (PARAMS)))
    error ("octave_calc_random: PARAMS must be a row of numbers.");
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
    error (strcat ("octave_calc_random: %s takes %d parameters, %s, and", ...
                   " %d were given."), DISTNAME, numel (names), ...
           strjoin (names, ", "), numel (PARAMS));
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

  ## The draw, under a seed that is always written out
  if (isempty (SEED))
    SEED = mod (floor (now () * 86400000), 2 ^ 31);
  endif
  for g = {'rand', 'randn', 'randp', 'rande', 'randg'}
    feval (g{1}, 'seed', SEED);
  endfor
  values = random (pd, nrows, ncols);

  ## The cells, as wide as the block or four, whichever is the greater
  width = max (ncols, 4);
  C = [pad(width, 'Random numbers'); pad(width); ...
       pad(width, 'Distribution', pd.DistributionName); ...
       named(width, names, PARAMS); ...
       pad(width, 'Size', nrows, 'by', ncols); ...
       pad(width, 'Seed', SEED); pad(width); ...
       [num2cell(values), cell(nrows, width - ncols)]];

endfunction

## A row per parameter, named as makedist names it
function R = named (width, names, values)
  R = cell (numel (names), width);
  for ii = 1:numel (names)
    R(ii,1:2) = {names{ii}, values(ii)};
  endfor
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
%! C = octave_calc_random ('Normal', [5, 2], 3, 4, 7);
%!test
%! assert_equal (size (C), [11, 4]);
%!test
%! assert_equal (C(1,1), {'Random numbers'});
%!test
%! assert_equal (C(3,1:2), {'Distribution', 'Normal'});
%!test
%! assert_equal (C(4:5,1:2), {'mu', 5; 'sigma', 2});
%!test
%! assert_equal (C(6,1:4), {'Size', 3, 'by', 4});
%!test
%! assert_equal (C(7,1:2), {'Seed', 7});
%!test
%! ## The same seed draws the same numbers again
%! R = octave_calc_random ('Normal', [5, 2], 3, 4, 7);
%! assert_equal (C(9:11,:), R(9:11,:));
%!test
%! ## A different seed does not
%! R = octave_calc_random ('Normal', [5, 2], 3, 4, 8);
%! assert_equal (isequal (C(9:11,:), R(9:11,:)), false);

%!test
%! ## A seed that was not given is chosen and written out just the same
%! R = octave_calc_random ('Normal', [5, 2], 2, 2);
%! assert_equal (R{7,1}, 'Seed');
%!test
%! R = octave_calc_random ('Normal', [5, 2], 2, 2);
%! assert_equal (isnumeric (R{7,2}) && R{7,2} >= 0, true);
%!test
%! ## and drawing again under it gives those numbers back
%! R = octave_calc_random ('Normal', [5, 2], 2, 2);
%! S = octave_calc_random ('Normal', [5, 2], 2, 2, R{7,2});
%! assert_equal (R(9:10,:), S(9:10,:));

%!test
%! ## A Poisson draw goes through randp, which rand and randn do not seed
%! R = octave_calc_random ('Poisson', 4, 1, 8, 3);
%! S = octave_calc_random ('Poisson', 4, 1, 8, 3);
%! assert_equal (R(8,:), S(8,:));
%!test
%! ## and a gamma draw through randg
%! R = octave_calc_random ('Gamma', [2, 3], 1, 8, 3);
%! S = octave_calc_random ('Gamma', [2, 3], 1, 8, 3);
%! assert_equal (R(9,:), S(9,:));

%!test
%! ## The block is as wide as the draw where that is wider than the heading
%! R = octave_calc_random ('Normal', [5, 2], 2, 7, 1);
%! assert_equal (size (R), [10, 7]);
%!test
%! ## and four wide where it is not
%! R = octave_calc_random ('Normal', [5, 2], 2, 1, 1);
%! assert_equal (size (R), [10, 4]);

%!test
%! ## Every parameter is named as makedist names it
%! R = octave_calc_random ('Stable', [1.5, 0, 1, 0], 2, 2, 1);
%! assert_equal (R(4:7,1), {'alpha'; 'beta'; 'gam'; 'delta'});

%!error<octave_calc_random: invalid number of input arguments.> ...
%! octave_calc_random ('Normal', [5, 2], 3)
%!error<octave_calc_random: DISTNAME must be a distribution makedist takes.> ...
%! octave_calc_random ('Gaussian', [5, 2], 3, 4)
%!error<octave_calc_random: PARAMS must be a row of numbers.> ...
%! octave_calc_random ('Normal', 'five', 3, 4)
%!error<octave_calc_random: NROWS must be a whole number of 1 or more.> ...
%! octave_calc_random ('Normal', [5, 2], 0, 4)
%!error<octave_calc_random: NCOLS must be a whole number of 1 or more.> ...
%! octave_calc_random ('Normal', [5, 2], 3, 1.5)
%!error<octave_calc_random: 1000 by 1000 is 1000000 numbers and the most that can be written is 100000.> ...
%! octave_calc_random ('Normal', [5, 2], 1000, 1000)
%!error<octave_calc_random: SEED must be a whole number of 0 or more, or nothing at all.> ...
%! octave_calc_random ('Normal', [5, 2], 3, 4, -1)
%!error<octave_calc_random: Normal takes 2 parameters, mu, sigma, and 1 were given.> ...
%! octave_calc_random ('Normal', 5, 3, 4)
%!error<octave_calc_random: Poisson takes 1 parameters, lambda, and 2 were given.> ...
%! octave_calc_random ('Poisson', [4, 5], 3, 4)
