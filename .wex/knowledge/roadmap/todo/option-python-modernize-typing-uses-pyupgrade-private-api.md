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
