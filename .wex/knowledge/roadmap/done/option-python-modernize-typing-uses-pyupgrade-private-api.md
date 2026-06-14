# modernize_typing: depends on pyupgrade's private `_fix_plugins` / `Settings`

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/modernize_typing_option.py:21`
**Agent**: agent:rectifier-correctness
**Bucket**: brittle-dependency
**Severity**: bug

## Symptom
```python
from pyupgrade._main import Settings, _fix_plugins
```
Both names live under a leading-underscore module (`_main`) and one of them is itself underscore-prefixed (`_fix_plugins`). They are explicitly **not** part of pyupgrade's public API. Any minor version bump of pyupgrade can rename them, change their signature, or remove them, and we will discover this in production. There is also no version pin documented at the call site.

## Suggested direction
Pick one of the following, in order of preference:
1. **Stable replacement**: switch to Ruff's typing modernizers (rule set `UP*`), which we already rely on elsewhere and which expose a stable public CLI / API. Cost: route through `WithBatchOptionMixin` like the JS Biome option, since Ruff is best invoked once per batch.
2. **Subprocess pyupgrade**: shell out to the `pyupgrade` CLI on a temp file. Slower per call but the CLI is the supported public interface — survives version bumps.
3. **Pin + comment**: keep the private import but pin pyupgrade in `pyproject.toml` to a known-good range and add an inline comment + a CI check that re-imports the symbols on each upgrade. Acceptable short-term but not the right long-term answer.

Document the choice in this option's docstring so the next maintainer doesn't reintroduce the brittle import.

## Resolution
Picked **option 1** (Ruff via `WithBatchOptionMixin`). Rationale: only path that combines modernity, public-API stability, idempotency, performance, and a future-consolidation path with sibling options (`RemoveUnusedOption`, `SortImportsOption`, `FormatOption`).

Concrete changes:
- `ModernizeTypingOption` now inherits from `WithBatchOptionMixin` and `_run_batch_on_paths` shells out to `python -m ruff check --select=UP --fix --fix-only --target-version=py312 --no-cache <paths>`. Using `sys.executable -m ruff` avoids PATH-activation dependencies.
- Non-zero exit raises a `RuntimeError` carrying stderr + stdout — matches `feedback_no_silent_errors`.
- `pyproject.toml`: removed `pyupgrade`, added `ruff`.
- Class docstring documents the choice + the rationale so the brittle private import doesn't sneak back in.
- Smoke-tested: ruff fixes `List[int]→list[int]`, `Optional[X]→X | None`, `Union[A, B]→A | B`. Second pass is a noop (idempotent). Unused `from typing import ...` left over by Ruff are picked up by `RemoveUnusedOption` (autoflake) in a subsequent pass — clean separation of concerns.
