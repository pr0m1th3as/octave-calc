# octave-calc

**Run GNU Octave analyses on the data in your LibreOffice Calc spreadsheet,
from inside LibreOffice.**

You stay in Calc. You select a range, pick one of your own Octave functions,
and the result is written back into the sheet. Core Octave and whatever
Octave packages you have installed stand behind those functions.

**This is not the same thing as
[GNU-Octave-CalcLink](https://github.com/VAZMFB/GNU-Octave-CalcLink), which
runs the arrow the other way**: that is an Octave class that drives Calc from
an Octave prompt, in order to produce formatted spreadsheet reports, and it is
Windows only. This project is a LibreOffice extension for a user who is
sitting in a spreadsheet and never opens an Octave prompt.

**This is not an Octave package.** There is no `DESCRIPTION`, no `inst/`, and
nothing here installs with `pkg`. It installs into LibreOffice.

## Status

**Nothing is built yet.** The project is an evaluation rather than a
commitment, and it is explicitly unmaintained until it proves it is wanted.
The first thing to appear will be a menu-driven prototype that hands a
selected range to Octave and writes the result back, which exists to find out
whether anyone wants Calc to call Octave at all.

## What it will need, once there is something to install

Two things have to line up on the user's machine:

1. LibreOffice, with this extension installed.
2. GNU Octave on `PATH`, with whatever Octave packages the user's own
   functions rely on.

If either is missing the extension says which one, rather than leaving a dead
menu entry behind.

## Layout, as it fills in

| Path | Holds |
|------|-------|
| `COPYING`, `LICENSE.txt` | GPL v3. |
| `python/` | The PyUNO component, which is where the work happens. |
| `oxt/` | `description.xml`, `META-INF/`, the `.xcu` configuration. |
| `tools/` | Build script that zips the `.oxt`. |

## Licence

GNU General Public License version 3. See `COPYING`.
