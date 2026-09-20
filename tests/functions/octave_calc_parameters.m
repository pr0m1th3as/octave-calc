## Copyright (C) 2026 Andreas Bertsatos <abertsatos@biol.uoa.gr>
##
## This file is part of the octave-calc extension.
##
## This program is free software: you can redistribute it and/or modify it
## under the terms of the GNU General Public License as published by the Free
## Software Foundation, either version 3 of the License, or (at your option)
## any later version.
##
## This program is distributed in the hope that it will be useful, but WITHOUT
## ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
## FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
## more details.
##
## You should have received a copy of the GNU General Public License along
## with this program.  If not, see <https://www.gnu.org/licenses/>.

## -*- texinfo -*-
## @deftypefn {octave-calc} {[@var{NAMES}, @var{NAME}] =} octave_calc_parameters (@var{DISTNAME})
##
## Return the parameter names of the distribution @var{DISTNAME}, one per
## row, and the name it calls itself by.  A fixture for the tests of
## @file{octave_stats.py}, which hold the generator registry against what the
## @code{statistics} package declares, and so must ask the package rather
## than the registry.
##
## @end deftypefn

function [NAMES, NAME] = octave_calc_parameters (DISTNAME)
  pd = makedist (DISTNAME);
  NAMES = pd.ParameterNames(:);
  NAME = {pd.DistributionName};
endfunction

%!test
%! assert_equal (octave_calc_parameters ('Normal'), {'mu'; 'sigma'});
%!test
%! [~, NAME] = octave_calc_parameters ('tLocationScale');
%! assert_equal (NAME, {'t Location-Scale'});
