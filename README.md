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

**Early, and explicitly unmaintained until it proves it is wanted.** Two
things work today: a menu of statistical analyses, and two spreadsheet
functions.

## The Statistics menu

`Data > Statistics with GNU Octave`, directly below Calc's own Statistics,
opens one dialog. You pick a category, then an analysis inside it, and the
dialog says what that analysis is for and when to use it instead of its
neighbours. You give it the range holding your data, say how that range is
laid out, set whatever the analysis offers, and name the cell the results
are written from. Nothing is overwritten without asking, and the results go
in as one undoable action.

An analysis states what it reads, and the dialog asks for it in those words:
two or more independent groups, one per column or per row or as two columns
of values and labels; measurements taken on the same subjects, a row per
subject; each value beside the two factors it was measured under; one
sample; or no cells at all.

Five categories: forty-six analyses of its own, and the Custom analysis,
which runs one of your own Octave functions the same way.

- **Group comparisons**, eleven. One-way ANOVA and two-way ANOVA, the
  two-sample, paired and one-sample t-tests, the Kruskal-Wallis and
  Mann-Whitney U tests, the Wilcoxon signed-rank test, the sign test, the
  Friedman test, and a test of equal variances. Welch's variant where it
  applies, and pairwise comparisons saying which groups differ.
- **Distribution fitting**, four. Tests of normality, goodness of fit,
  distribution fitting with a confidence interval per parameter, and
  outlier detection.
- **Random numbers**, twenty-six. A generator per distribution, drawing
  into the range you select. It returns the numbers and nothing else.
- **Experimental design**, five. Sample size, power and detectable
  difference, each solving for one quantity, and the full and two-level
  factorial designs.
- **Custom analysis**. Your own Octave function, from a folder you add,
  with four inputs and a field of name and value pairs, and up to three
  results written where you say. Where the sandbox runs, a core or package
  function may be named instead.

Association tests, regression models and multivariate analyses are not there
yet. Each will appear with the analyses that fill it.

## Spreadsheet functions

The two functions are:

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

## Settings

The settings are under `org.octavecalc.Settings` in Tools > Options > Advanced
> Open Expert Configuration: the full path of the `octave-cli` to run, the
folders holding your own functions, the packages to load, the memory and
`/tmp` sizes, and the time limits. With `Octave` empty, the extension looks
for `octave-cli` itself; a path given there is the only one tried.

## Requirements

On the user's machine:

1. LibreOffice, with this extension installed.
2. GNU Octave, and the Octave packages the user's functions rely on. Its
   `octave-cli` is found on `PATH`, on Windows in the installer's usual
   place, on macOS where Homebrew or MacPorts put it, or wherever the
   `Octave` setting says.
3. The Octave package `devtools`, version 0.2.1 or later, which runs the
   server and its sandbox.
4. The Octave package `statistics`, which every analysis in the menu loads,
   and `datatypes` beneath it. The spreadsheet functions need neither.
5. For cells, a sandbox: on Linux `bwrap` from the `bubblewrap` package and
   `prlimit` from `util-linux`, on macOS the system's `sandbox-exec`. Windows
   has none yet, so there only the Statistics menu runs.

Where a systemd user session is running, Octave is started through it, which
lets the sandbox work when LibreOffice itself runs under an AppArmor profile.

## Layout

| Path | Holds |
|------|-------|
| `COPYING`, `LICENSE.txt` | GPL v3 or later. |
| `docs/` | What GitHub Pages serves: the release notes and the extension update feed. |
| `python/` | The component, the Octave runner behind it, and the settings reader. |
| `octave/` | One Octave function per analysis, and the helpers they share. |
| `idl/` | The interface the cell functions call, compiled into the package. |
| `oxt/` | `description.xml`, `META-INF/`, the function registration and the settings schema. |
| `tools/` | `build_oxt.py`, which compiles and packages the extension, and `publish_release.py`, which writes `docs/` at each release. |
| `tests/` | Tests, run with `python3 -m unittest discover tests`. |

## Licence

GNU General Public License, version 3 or (at your option) any later
version. See `COPYING`.
