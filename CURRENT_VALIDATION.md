# Candidate source validation — 2026-10-03

Candidate source version: **0.3.3**. No candidate release was published;
public 0.3.2 artifacts and historical evidence remain unchanged.

## Engine/RL integration follow-up

The structured verdict classifier now requires complete recognized Lean native
false-decision diagnostics for mathematical rejection. Unknown exit-1 failures,
truncated output and mixed diagnostics are operational errors. CLI and formatted
LSP prefixes are covered. The diagnostic contract comes from Lean 4.23.0's
`tests/lean/run/decideNative.lean`; this is conservative diagnostic interpretation,
not an exported counterexample or a replacement for current native validation.

The JSON CLI rejects duplicate object keys, including nested specification keys,
and catches decoder nesting failures before native execution. Existing handling
for wrapper timeout/failure exits, signals, unexpected exits and execution-time
OS errors remains in place. The sweep now uses the same status classifier.

The article was rewritten around a generated count check, leastness, complete
pair enumeration, the recorded representation optimization, and explicit native
compiler/translator trust. Its Lean excerpt matches the actual generated
`examples/generated_count.lean` core modulo whitespace. Specification serialization,
arithmetic semantics and result fields have not changed.

Fresh source result on Python 3.12.14: **85 passed, 10 live/platform skips,
40 subtests passed**. Diff hygiene and independent arithmetic examples pass.
The joint artifact/checking record is maintained in MathCheck RL's
`docs/CURRENT_VALIDATION.md` after synchronizing its immutable Engine dependency.

This worker has no `/proc` and no stock Lean on PATH. A direct bubblewrap
capability probe exits 1 with `Can't read /proc/sys/kernel/overflowuid`.
Live Lean tests are skipped; no current native acceptance or rejection is claimed.
Run both live suites, the positive/negative controls and the installed-wheel gate
on supported Linux with Lean 4.23.0 before publishing.

## Earlier candidate evidence

Before this follow-up, the previous worker recorded **63 tests, 10 skips and
38 subtests**, four candidate wheel builds and installed-package structural checks.
It installed the official Lean 4.23.0 archive, SHA-256
`ecd028d6f642b61b451c8687aeeb24dd53789fbfdcb7d4adb8f5cf60eb2022ba`;
the binary SHA-256 was
`cbf5fd536e142ef1beaccf33f788fd8a7f3f29fb214e75c11319a8d8677b4b2b`.
Stock Lean exited 1 with `error: failed to locate application` because its
Linux application-path lookup needed unavailable `/proc/<pid>/exe`.
Bubblewrap also failed its capability probe.

Its six quickstart controls and 39 procedural/dataset trials all returned
operational errors, supplying no acceptance evidence. The release gate stopped
at the version probe. These records remain historical, not fresh evidence for
this source. Earlier Actions runs were blocked by an account billing lock.

Remaining limits include diagnostic-format dependence, trusted expression
translation, and production isolation beyond per-process limits. Isolation is
opt-in in Engine; RL requires the explicitly configured isolated launcher.
No Mathlib installation is required for the current bounded checkers.
