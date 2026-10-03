# Candidate source validation — 2026-10-03

Candidate source version: **0.3.3**. This does not replace the public 0.3.2
release assets or their historical evidence. No candidate release was published.

Wrapper timeouts/failures, signals, unexpected exits and launch errors are
classified as operational failures. The README separates scalar contracts,
complete pair certificates and finite observation checking, including compiler
and translator trust. CI exports `LEAN_BIN` in the same step as pytest.

The fresh locked Python 3.12.14 environment resolves dependencies and passes
**63 tests, with 10 live/platform skips and 38 subtests passed**. The versioned
source wheel builds; companion candidate packaging is documented in MathCheck
RL's `docs/CURRENT_VALIDATION.md`.

Lean 4.23.0 is now installed from the official Linux archive. Its verified
archive SHA-256 is
`ecd028d6f642b61b451c8687aeeb24dd53789fbfdcb7d4adb8f5cf60eb2022ba`;
the installed `bin/lean` SHA-256 is
`cbf5fd536e142ef1beaccf33f788fd8a7f3f29fb214e75c11319a8d8677b4b2b`.
The stock CLI exits 1 with `error: failed to locate application`: its Linux
application-path discovery requires `/proc/<pid>/exe`, unavailable in this
workspace. Bubblewrap also exits 1 because `/proc/sys/kernel/overflowuid` is
missing. Installation cannot resolve these OS capability failures.

The six companion quickstart controls and 39 procedural/dataset control trials
all return **operational_error**, with no acceptance evidence. The full release
gate stops at `lean --version`, before building or native artifact smoke. No
unisolated reward fallback was added. Earlier Actions jobs were prevented from
starting by the GitHub account billing lock.

Run complete live suites and the companion manual **Native release candidate
gate** workflow on supported Linux before publishing. Remaining limits include
unidentified infrastructure failures returning exit 1, trusted expression
translation, and production isolation beyond per-process limits. No Mathlib
installation is required for these current bounded checkers.
