# MathCheck Engine 0.3.2 release evidence

MathCheck Engine 0.3.2 is a corrective metadata release. It changes the
declared Python compatibility range to `>=3.11,<3.14`, removes the incorrect
Python 3.10 classifier, adds Python 3.13, and adds a regression test binding the
project metadata to the runtime version. It does not change verifier semantics
or add a mathematical contract.

- Git commit: `742edec6bdb4f7057780fc54e98fb284b76eedcf`
- Git tag: `v0.3.2`
- Public release: <https://github.com/stanleyngugi/mathcheck-engine/releases/tag/v0.3.2>
- Python tests with live Lean: 71 passed
- Generated subtests: 42 passed
- Tested Lean version: 4.23.0
- Lean executable SHA-256: `cbf5fd536e142ef1beaccf33f788fd8a7f3f29fb214e75c11319a8d8677b4b2b`
- Wheel SHA-256: `61f5d485d59b77270df4134c0dd332afe9fbd7b7596baa85400341b85259bd4d`
- Release-manifest SHA-256: `b58de70188f2ff2a454197f212415b7d58a7b440ca20006641ba16e264eada1b`

The complete MathCheck release gate ran twice from clean temporary
environments with `SOURCE_DATE_EPOCH=1704067200`. Both runs produced
byte-identical Engine, RL core, sequence, and Hub wheels. Each run installed
the wheels outside both source trees, passed `pip check`, loaded both
environments, and used the dedicated read-only Lean toolchain to accept a known
correct bounded result and reject a known incorrect result.

This evidence is reproducibility and regression evidence, not a proof that the
implementation has no defects, that an upstream prose-to-specification
translation is faithful, or that the isolation wrapper is an audited
multi-tenant security boundary.
