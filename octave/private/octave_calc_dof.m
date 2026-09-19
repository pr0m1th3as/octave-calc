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
## @deftypefn {octave-calc} {@var{TBL} =} octave_calc_dof (@var{TBL})
##
## An analysis of variance table with its degrees of freedom named as every
## other result of Data > Statistics with GNU Octave names them.
##
## @var{TBL} is the table an @code{anova} function returns, whose first row
## holds its headings.  A heading of @qcode{'df'} becomes @qcode{'DoF'};
## where the table also holds @qcode{'dfe'}, the two are the numerator and
## the denominator of an F statistic and become @qcode{'Numerator DoF'} and
## @qcode{'Denominator DoF'}.  Every other heading is left as it is.
##
## @end deftypefn

function TBL = octave_calc_dof (TBL)

  heading = TBL(1,:);
  text = cellfun (@ischar, heading);
  if (any (text & strcmp (heading, 'dfe')))
    heading(text & strcmp (heading, 'df')) = {'Numerator DoF'};
    heading(text & strcmp (heading, 'dfe')) = {'Denominator DoF'};
  else
    heading(text & strcmp (heading, 'df')) = {'DoF'};
  endif
  TBL(1,:) = heading;

endfunction
