# Naming and compatibility

## Public name

The project is **MathCheck Engine**: a verification engine for bounded integer
computations and complete finite-pair certificates. The intended future GitHub
repository slug is `mathcheck-engine`.

The name is deliberately concrete. It does not imply that every Lean theorem is
reduced by the kernel alone, and it does not imply universal coverage of
mathematics. Some checks use Lean's `native_decide`, which adds the compiler and
native runtime to the trusted computing base.

## Stable 0.x compatibility names

The following technical names remain unchanged through the 0.x line:

- PyPI/distribution name: `lean-kernel-verifier`
- Python import: `lean_kernel_verifier`
- isolation executable: `lean-isolated`
- environment variable prefix: `LKV_`

Renaming these identifiers now would make the downstream environment and saved
release manifests needlessly fragile. A future 1.0 migration may introduce
aliases first, with a documented deprecation window; it must not silently break
existing manifests.

## Relationship to MathCheck RL

MathCheck Engine owns specification validation, trusted source generation,
checker execution, isolation, and evidence-rich result contracts. MathCheck RL
builds tasks, prompts, rewards, caching, splits, and training-framework adapters
on top of this engine. Neither project includes the separate experimental math
solver or its benchmark results.
