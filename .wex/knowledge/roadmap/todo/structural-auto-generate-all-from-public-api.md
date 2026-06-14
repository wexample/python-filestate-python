# Structural: auto-generate `__all__` from declared public API

**Source**: *(new option — `option/python/auto_generate_all_option.py`)*
**Agent**: agent:rectifier-design
**Bucket**: structural
**Severity**: feature

## Background
`__all__` controls what `from module import *` exposes and signals public API to tooling (mypy public-API detection, sphinx autodoc, etc.). In our codebase it's either missing or hand-maintained — both fail modes are common (new public class added, forgot to update `__all__`; private helper accidentally exported because someone copied a pattern).

## Suggested direction
LibCST visitor over a module:
1. Collect top-level public symbols: `ClassDef.name.value`, `FunctionDef.name.value`, `Assign` targets that are `Name` and not starting with `_`, `TypeAlias.name.value`.
2. **Filter out**: re-exported names already covered by an `if TYPE_CHECKING:` block (those are typing-only).
3. Build sorted list (`sorted(names)` — matches the rest of our ordering conventions).
4. Locate existing `__all__` assignment, if any. Compare to computed list. If equal: no-op. Otherwise: replace with the computed list.
5. Insert at the correct position via the existing `target_index_for_module_metadata` helper — `__all__` is recognized metadata, so this composes with `OrderModuleMetadataOption`.

**Opt-in only**: this is opinionated. Some files (CLI entry points, fixtures, conftests) shouldn't have `__all__`. Gate via a per-target option flag (`auto_all: true`) or a top-of-file marker (`# filestate: auto-all`).

**Bail on `__init__.py`** by default — barrel imports there have their own logic and conventions, often hand-curated.
