# octave-calc

**Run GNU Octave analyses on the data in your LibreOffice Calc spreadsheet,
from inside LibreOffice.**

You stay in Calc. You call one of your own Octave functions, or one from core
Octave or an installed package, on the cells of your sheet, and the result is
written back into the sheet.

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
works today are two spreadsheet functions:

    =OCTAVE("mean", A1:C2, 2, "omitnan")
    =OCTAVE("interp1", OCTRANGE(A1:A10), B1:B10, "linear")
    =OCTAVE("lasso", A1:D100, E1:E100, OCTRANGE(G1:H8, "pairs"))

`OCTAVE` takes a function name and up to 16 arguments, in any order: numbers,
text, or ranges. A range passed as it is arrives as its values. Wrapped in
`OCTRANGE`, it keeps its dates, times, logical values and error cells; with
the mode `"pairs"`, a range of two columns, names then values, is passed as
name-value arguments.

A cell holding `OCTRANGE` alone shows its range and mode, such as
`J1:J4 (data)`, while its value is still what `OCTAVE` reads, so a formula can
refer to that cell instead of repeating `OCTRANGE`. A cell you have formatted
yourself keeps your format.

A `NaN` result shows as `#N/A`, and `Inf` or `-Inf` as `#NUM!`. Read through
`OCTRANGE`, a `#N/A` cell is a missing value again, `NaN` or `NaT` for a date,
while any other error cell is refused, naming the cell. Calc stops a plain
reference to an error cell before the function is called: a single cell shows
that error, and a range shows `Err:504`. **Wrap a range that may hold `#N/A`
in `OCTRANGE`.**

A result of more than one cell is entered as an array formula: select the
output range, then Ctrl+Shift+Enter, since Calc has no spilling. Results
recalculate when their source cells change, and a repeated call with
unchanged inputs is answered from a cache.

**Cells run only in a sandbox**: no network, no other program can be started,
nothing on disk can be written, and only the folders and packages you choose
are visible. A call is stopped after 10 seconds. Where no sandbox can run,
no cell is evaluated, and the cell says why. The Statistics menu runs its
analyses with or without a sandbox, since what it runs comes from the
extension and never from the document; when a sandbox that should work
fails, it says so once.

The settings are under `org.octavecalc.Settings` in Tools > Options > Advanced
> Open Expert Configuration: the folders holding your own functions, the
packages to load, the memory and `/tmp` sizes, and the time limits.

A menu-driven workbench for longer analyses, which a formula cannot host
because Calc waits for a formula to return, is the next piece.

## Requirements

On the user's machine:

1. LibreOffice, with this extension installed.
2. GNU Octave, with `octave-cli` on `PATH`, or on Windows in the installer's
   usual place, and the Octave packages the user's functions rely on.
3. The Octave package `devtools`, version 0.2.1 or later, which runs the
   server and its sandbox.
4. For cells, a sandbox: on Linux `bwrap` from the `bubblewrap` package and
   `prlimit` from `util-linux`, on macOS the system's `sandbox-exec`. Windows
   has none yet, so there only the Statistics menu runs.

Where a systemd user session is running, Octave is started through it, which
lets the sandbox work when LibreOffice itself runs under an AppArmor profile.

## Layout

| Path | Holds |
|------|-------|
| `COPYING`, `LICENSE.txt` | GPL v3. |
| `python/` | The component, the Octave runner behind it, and the settings reader. |
| `idl/` | The interface the cell functions call, compiled into the package. |
| `oxt/` | `description.xml`, `META-INF/`, the function registration and the settings schema. |
| `tools/` | `build_oxt.py`, which compiles and packages the extension. |
| `tests/` | Tests, run with `python3 -m unittest discover tests`. |

## Licence

GNU General Public License version 3. See `COPYING`.
