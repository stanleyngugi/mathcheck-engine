# Source validation — 2026-10-03

This audit updates source on `main`; it does not replace the public 0.3.2
release artifacts or their evidence.

- Wrapper timeout/failure exits, signals, unexpected process exits and launch
  errors are classified as operational failures rather than mathematical rejection.
- The README distinguishes scalar contracts, complete pair certificates and
  finite observation checking, including native compiler/translator trust.
- CI exports `LEAN_BIN` before pytest in the same shell step, enabling its live
  tests instead of relying on a variable visible only to subsequent steps.

Local result on Python 3.12.14: **63 passed, 10 skipped, 38 subtests passed**.
All four companion-project source wheels built and imported outside their source
trees. The installed v1 smoke exercised invalid-input scoring without native
execution. Diff hygiene passed.

Lean is absent in this workspace; bubblewrap failed its capability probe because
`/proc/sys/kernel/overflowuid` is unavailable. Native integration checks were
skipped and the full release gate was not run. Earlier GitHub Actions jobs were
blocked by an account billing lock. These source results must not be presented
as new live Lean evidence or a new release.

Remaining limits include unidentified infrastructure failures that return exit 1,
trusted expression translation, and production isolation beyond per-process
limits. Run the live suites and companion quickstart/control profiler on supported
Linux with Lean 4.23.0, then version and gate new artifacts before publication.
