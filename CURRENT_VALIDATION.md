# Fresh Engine closeout attempt — 2026-10-04

**0.3.3 remains unpublished; native release validation is blocked.**
The exact source tested and built was
`dce2fc88cee1e98ed3136ac89a4b40eba0d1ada7`. GitHub main matched that commit
before this evidence-only update. No runtime or package metadata changed.

A subsequent [VM preflight follow-up](validation/2026-10-04-linux-attempt/VM_PREFLIGHT_FOLLOWUP.md)
overcame the earlier image download failure and booted Ubuntu under QEMU TCG.
Stock Lean 4.23.0 started and an unprivileged bubblewrap namespace probe passed
inside that guest. The transient worker was replaced before the full gate ran
or guest files were exported. The follow-up is a transcription of observed tool
results, not a retained full native test report. No native contract or release
pass is claimed. The latest inspected Engine Actions run received no runner and
started zero steps. A persistent local Linux host or guest must run the unchanged
native gates; WSL is not required for the documented QEMU route.

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

## Warning-prefixed diagnostic regression and local native attempt — 2026-10-05

Reproduced a Lean 4.23.0 false-decision output that includes a normal unused
variable warning and its `Note:` continuation before the complete
`native_decide` rejection. The conservative diagnostic classifier previously
treated that recognized mathematical rejection as an operational error. The
narrow parser fix ignores only a syntactically valid Lean warning header, its
indented continuation and one attached `Note:` block before applying the
existing complete-diagnostic check. Unknown output remains operational. The
regression suite passes 19 tests, and the corresponding real-Lean positive and
negative pair-certificate test passes against the verified 4.23.0 binary.

The fix is commit `fa2f04ce4a1d114f08444944dbf0898515611980` on top of the
handed-off `af26078be4a316f29be8b10cdc17d30ea1651cab`. The joint artifact/native
gate then passed source tests, four wheel builds, clean installed-consumer
checks, structural smoke, Lean startup and quickstart in the persistent Ubuntu
24.04 guest. The unchanged Engine live-suite stage exceeded its 900-second gate
limit under QEMU TCG software emulation (`900.218s`); the report remains failed,
and later required native checks did not run. A separate verbose execution of
the unchanged Engine suite eventually completed against genuine Lean 4.23.0:
**96 passed, 52 subtests passed in 1,488.11 seconds**. This confirms a time-limit
problem in TCG; it is diagnostic evidence, not a passing closeout gate. The
[summary](https://github.com/stanleyngugi/mathcheck-rl/blob/main/docs/evidence/native-engine-diagnostic-20261005-tcg.json)
and [full transcript](https://github.com/stanleyngugi/mathcheck-rl/blob/main/docs/evidence/native-engine-diagnostic-20261005-tcg.txt)
are preserved. No
Windows skip or targeted test is being represented as completion. The machine
has no existing Linux host and firmware virtualization is currently disabled;
cloud compute and publication remain unauthorized until explicitly approved.
See MathCheck RL's
[`native-closeout-20261005-local.json`](https://github.com/stanleyngugi/mathcheck-rl/blob/main/docs/evidence/native-closeout-20261005-local.json)
for the exact joint-gate report and wheel hashes, plus the
[`Engine diagnostic summary`](https://github.com/stanleyngugi/mathcheck-rl/blob/main/docs/evidence/native-engine-diagnostic-20261005-tcg.json)
and [full test log](https://github.com/stanleyngugi/mathcheck-rl/blob/main/docs/evidence/native-engine-diagnostic-20261005-tcg.txt).

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

## Final joint native closeout — 2026-10-05

The unchanged MathCheck joint gate passed on Engine
`2556e1fec67aabb8823fed10d170df7f42ebf574` and RL
`62c988f428f35c484b1d851ffb5b5fcb130eb619`. It ran in Ubuntu 24.04.4 under
QEMU WHPX with hardware acceleration confirmed by `-accel
whpx,kernel-irqchip=off`, using unprivileged Python 3.12.3, bubblewrap 0.9.0,
and stock read-only Lean 4.23.0. The official Lean archive digest is
`ecd028d6f642b61b451c8687aeeb24dd53789fbfdcb7d4adb8f5cf60eb2022ba`; the Lean
binary digest is `cbf5fd536e142ef1beaccf33f788fd8a7f3f29fb214e75c11319a8d8677b4b2b`.

Engine's full live suite passed **96 tests and 52 subtests in 424.30 seconds**.
The joint gate exited 0 in 801.238 seconds with native validation complete and
release readiness true. The complete unmodified report, stage logs, procedural
and dataset controls, wheel manifest, environment provenance and precise
optional-skip record are retained in MathCheck RL's
[native closeout evidence](https://github.com/stanleyngugi/mathcheck-rl/tree/main/docs/evidence/native-closeout-whpx-20261005-final).
The only skip was the optional PyTorch-backed RL training test module; required
native skips were zero. Reproducible Engine 0.3.3 wheel SHA-256:
`da94438427e02382c80dcf366c540c3e625e552966d7c873516aaca7790f6782`.

This passing WHPX run supersedes the earlier TCG timeout and failed WHPX boot
diagnostics below.

## Publication and fresh-consumer closeout — 2026-10-05

The validated [Engine 0.3.3 release](https://github.com/stanleyngugi/mathcheck-engine/releases/tag/v0.3.3)
is published with immutable tag target
`2556e1fec67aabb8823fed10d170df7f42ebf574`. Its downloaded release wheel hash
matches the joint native gate manifest:
`da94438427e02382c80dcf366c540c3e625e552966d7c873516aaca7790f6782`.

The validated [RL 0.2.2 release](https://github.com/stanleyngugi/mathcheck-rl/releases/tag/v0.2.2)
and Prime Hub `stanley-ngugi/mathcheck-rl@0.1.2` are also published. Prime
reports the candidate as public runtime v1. Fresh Prime CLI and Ubuntu WHPX
consumer installs passed `pip check`; the Linux consumer ran all six valid,
invalid, minimum and pair certificate controls against the installed Hub
package using isolated Lean 4.23.0. Full Prime identity, source pin, artifact
hash and native consumer evidence is in MathCheck RL's
[publication closeout record](https://github.com/stanleyngugi/mathcheck-rl/blob/main/docs/evidence/native-closeout-whpx-20261005-final/publication.json).

The joint native gate and installed-consumer checks passed. The only source
suite skip is optional RL training coverage requiring PyTorch; no required
native checks were skipped.
