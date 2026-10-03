# Additional execution attempts

This follow-up tried to obtain a genuine Linux guest rather than repeat skipped
tests or change the verification requirements. Native certification remains
incomplete. Engine implementation and package metadata are unchanged.

## Local capabilities

`unshare --mount --fork /bin/true` exits 1 with `Operation not permitted`.
The separate user-namespace probe already recorded in this directory fails
because `/proc/self/uid_map` is absent. The latest Engine CI run at evidence
commit `8097d2bdb16bc40ebcde43cb1f92083b8f521b59`,
[37156000537](https://github.com/stanleyngugi/mathcheck-engine/actions/runs/37156000537),
also has zero steps and runner ID 0. No workflow retry was scheduled here.

## QEMU

The [Microsoft Quicksand project](https://github.com/microsoft/quicksand)
provides packaged QEMU and Ubuntu guests for Linux and Windows. Its official
[installation documentation](https://github.com/microsoft/quicksand/blob/main/docs/user-guide/01-installation.md)
describes software emulation as a fallback without Docker or administrator
access. This offers a potential Windows route without reinstalling WSL; it has
not yet passed MathCheck's gates.

The `quicksand-qemu==0.5.12` Linux wheel was downloaded from PyPI and installed
under the task workspace. Its SHA-256 is
`5a63f03c67fd9fa2343a6b81a0b60af0aab5465f926add8a96e1a845882ab308`.
With the bundled library path and `QEMU_MODULE_DIR` configured, the binary
reports QEMU 8.2.2, Ubuntu package `1:8.2.2+ds-0ubuntu1.16`. A paused,
guestless TCG process starts and runs until the deliberate five-second stop.
This is initialization evidence only, not a booted VM or a native Lean pass.
The command, result, and binary hash are in `vm-attempt.json`.

The required Ubuntu 0.10.0 platform wheel is 308,561,313 bytes, with published
SHA-256 `c1490d1e9a16c0160f3d05c1c7dd07d62d1a4bdae28158f94b53fe8d0998644e`.
It was not obtained:

- Ordinary Ubuntu repository/cloud-image downloads timed out at the proxy.
- The official Quicksand index resolves the correct platform wheel, but its
  GitHub asset download timed out and a bounded retry ended in repeated 503s.
- The relevant combined Linux Actions artifact is 5,632,195,992 bytes; the
  connector rejected it against its 536,870,912-byte download maximum before
  downloading.
- The browser release-link download timed out and left a `chrome-error` page
  for the asset host. The browser's URL policy rejected inspecting that error
  page. No complete guest-image file was returned or synchronized.

No guest was booted, and no VM/native acceptance is claimed. Software emulation
may be slow; a future worker must preserve the existing required test outcomes
and explicitly report real timeouts rather than relabel them as passes.

## Remaining dependency on an external execution surface

A Windows local agent can investigate the documented Quicksand/QEMU Ubuntu
route without WSL, or use an existing supported Linux runner. It must first
prove that the guest has a real `/proc`, working bubblewrap namespaces and a
healthy stock Lean 4.23.0. Installation or QEMU process startup alone is not
that proof. The four finite release gates remain those in this directory's
README. Prime publication remains contingent on the downstream joint gate and
authenticated access to the environment owner account.
