# Fresh Engine closeout attempt — 2026-10-04

**0.3.3 remains unpublished; native release validation is blocked.**
The exact source tested and built was
`dce2fc88cee1e98ed3136ac89a4b40eba0d1ada7`. GitHub main matched that commit
before this evidence-only update. No runtime or package metadata changed.

A subsequent [VM execution attempt](validation/2026-10-04-linux-attempt/VM_ATTEMPT.md)
installs QEMU and demonstrates TCG initialization, but cannot obtain its Ubuntu
guest image through the available download routes. No guest or native pass is
claimed. The latest Engine Actions run also received no runner and started zero
steps. A Windows Quicksand/QEMU route without WSL is documented for a local
agent; it still must pass the unchanged native gates.

The [full report and logs](validation/2026-10-04-linux-attempt/README.md)
record fresh source, build, installed-wheel, stock Lean, and isolation attempts:

- Without `LEAN_BIN`: **85 passed, 10 required skips, 40 subtests passed**.
- With the downloaded stock Lean explicitly configured: exit 1,
  **19 failed, 87 passed, 41 subtests passed**, no skips. The summary includes
  failed unittest subtests; all ten required live entries were attempted and
  none cleared its complete gate. This is not native acceptance evidence.
- Two candidate wheels are byte-identical, SHA-256
  `11dca4da84c56c4f045fe1e58c959db8a3d1490bdc6a78f4d97d4b871b45bca7`.
  Supplementary source archives build with identical file contents but differ
  in archive bytes; they are not claimed as repeatable release artifacts.
- A fresh wheel environment outside the checkout passes `pip check`. All 23
  package Python files match the wheel and audited source. Installed CLI
  duplicate-key/invalid-input controls and operational-error controls pass;
  a real subprocess timeout is demonstrated with an explicitly non-Lean fixture.
- The official Lean 4.23.0 archive and extracted binary hashes match the recorded
  fingerprints below. Nevertheless, the stock version probe exits 1 with
  `error: failed to locate application`. This worker has no `/proc` directory.
  Bubblewrap 0.9.0 and a separate namespace attempt both fail on missing `/proc`
  entries. Configured installed `lean-isolated` exits 125; no fallback was used.

**Zero current native mathematical acceptances or rejections were established.**
The report gives exact commands, dependencies, provenance, structured results,
artifact hashes, and four finite remaining gates: capable Linux execution,
complete native source checks, fresh installed isolated consumer checks, then
verified GitHub publication. No required PyPI step was established. RL's
candidate pin remains the audited source above; an evidence-only commit adds
no compatibility change. Later implementation/metadata changes require new
immutable RL pins, rebuilding, and joint native validation before Prime Hub.

---

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
