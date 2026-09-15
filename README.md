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

**Early, and explicitly unmaintained until it proves it is wanted.** What
works today is the spreadsheet function:

    =OCTAVE("mean", A1:C2)
    =OCTAVE("mean", A1:C2, 2, "omitnan")

The range is the function's first argument and anything after it is passed
along. A result of more than one cell is entered as an array formula: select
the output range, then Ctrl+Shift+Enter, since Calc has no spilling. Results
recalculate when their source cells change, and a repeated call with
unchanged inputs is answered from a cache without starting Octave at all.

A menu-driven workbench for longer analyses, which a formula cannot host
because Calc waits for a formula to return, is the next piece.

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
| `python/` | The component and the Octave runner behind it. |
| `idl/` | The interface a cell formula calls, compiled into the package. |
| `oxt/` | `description.xml`, `META-INF/`, the `.xcu` registration. |
| `tools/` | `build_oxt.py`, which compiles and packages the extension. |

## Licence

GNU General Public License version 3. See `COPYING`.
