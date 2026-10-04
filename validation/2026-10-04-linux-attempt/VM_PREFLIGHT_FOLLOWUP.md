# Booted guest preflight follow-up — 2026-10-04

The guest-image acquisition blocker in `VM_ATTEMPT.md` was subsequently overcome.
The following observations are transcribed from this conversation's execution
tool results. The transient worker was replaced before the complete native gate
ran and before its guest files could be exported. These are **preflight
observations, not a retained full native validation report or release approval**.

## Official image acquisition

This exact canonical encoded release URL downloaded successfully with pip:

```sh
python -m pip download --no-deps --retries 0 --timeout 30 --dest ./images \
  'https://github.com/microsoft/quicksand/releases/download/quicksand-ubuntu%2Fv0.10.0/quicksand_ubuntu-0.10.0-py3-none-manylinux_2_17_x86_64.whl'
```

The 308,561,313-byte wheel's SHA-256 matched the official release digest:
`c1490d1e9a16c0160f3d05c1c7dd07d62d1a4bdae28158f94b53fe8d0998644e`.
It contained the Ubuntu kernel, initrd and disk, unlike the small PyPI image stub.
Use the official wheel and digest for the local host architecture; this wheel
is for Linux x86_64, not Windows.

Host packages were `quick-sandbox==0.12.0`, `quicksand-core==0.13.0`,
`quicksand-qemu==0.5.12`, and `quicksand-ubuntu==0.10.0`. QEMU reported 8.2.2.
The guest used TCG software emulation, 4 GiB RAM and two virtual CPUs.
Its network mode was `MOUNTS_ONLY`; host files were supplied through SMB.
The restricted outer host refused Unix sockets. The temporary launcher used
Quicksand's existing authenticated loopback TCP agent transport and QEMU thread
disk I/O instead. Engine code and its isolation policy were unchanged.

## Actual guest observations

The guest command returned exit 0 and reported:

- Ubuntu **24.04.4 LTS**, kernel **6.8.0-110-generic**, x86_64.
- A real `/proc`, including `/proc/self/exe` resolving to the guest executable.
- Python **3.12.3** and guest `prlimit`.
- Stock Lean: `Lean (version 4.23.0, x86_64-unknown-linux-gnu, commit
  50aaf682e9b74ab92880292a25c68baa1cc81c87, Release)`.

The Lean version probe executed the previously downloaded official distribution
through the host mount. It was **not** an installed isolated consumer check.
The archive and binary fingerprints remain those recorded in `CURRENT_VALIDATION.md`.

A separate bootstrap command also returned exit 0. It created the guest user
`validator`, reported bubblewrap **0.9.0**, and successfully executed:

```sh
su -s /bin/sh validator -c \
  'bwrap --unshare-all --ro-bind / / --proc /proc --dev /dev /bin/true'
```

This is a real unprivileged namespace capability probe. The probe mounts the
guest root and does **not** substitute for the Engine's restrictive launcher or
its filesystem, environment and network tests. The bootstrap supplied the
outer host's bubblewrap executable and CPython 3.12 `ensurepip` module; a local
agent should prefer the guest distribution's ordinary packages and record
their actual provenance.

## Still required

There is no exported full source/live suite, isolated contract result, complete
installed consumer gate, joint release manifest, or publication from this guest.
Toolchain extraction into a separately owned read-only guest directory was
started; its completion was not observed. The guest and scratch files are no
longer available. Recreate a persistent local guest and run the unchanged joint
closeout gate. No native mathematical acceptance or rejection is claimed here.

Prime's secure method-choice prompt worked, but choosing Google reached
`502 Bad Gateway` / `Connection refused` before a credential form loaded.
No signed-in owner state or Prime upload was established. This cloud-browser
failure does not establish whether the owner's ordinary local browser works.
