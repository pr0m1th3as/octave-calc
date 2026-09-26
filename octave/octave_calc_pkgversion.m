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
## @deftypefn {octave-calc} {@var{V} =} octave_calc_pkgversion (@var{NAME})
##
## Version of a loaded package, for Data > Statistics with GNU Octave.
##
## @code{@var{V} = octave_calc_pkgversion (@var{NAME})} returns the version
## of the package @var{NAME} that is loaded, as text such as
## @qcode{'1.9.4'}, and empty text where no package of that name is loaded.
## Where the same package is installed both for the user and for everyone,
## the loaded one is the one reported.
##
## @seealso{pkg}
## @end deftypefn

function V = octave_calc_pkgversion (NAME)

  ## Input validation
  if (nargin != 1)
    error ("octave_calc_pkgversion: invalid number of input arguments.");
  endif
  if (! (ischar (NAME) && isrow (NAME)))
    error ("octave_calc_pkgversion: NAME must be a character vector.");
  endif

  V = "";
  installed = pkg ("list", NAME);
  for i = 1:numel (installed)
    if (installed{i}.loaded)
      V = installed{i}.version;
    endif
  endfor

endfunction

%!test
%! pkg load statistics
%! V = octave_calc_pkgversion ('statistics');
%! assert_equal (isempty (regexp (V, '^\d+\.\d+\.\d+$', 'once')), false);
%!test
%! assert_equal (octave_calc_pkgversion ('octave_calc_no_such_package'), '');

%!error<octave_calc_pkgversion: invalid number of input arguments.> ...
%! octave_calc_pkgversion ()
%!error<octave_calc_pkgversion: NAME must be a character vector.> ...
%! octave_calc_pkgversion (1)
