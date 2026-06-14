# New rule: forbid `from X import *` and resolve to explicit names when possible

**Source**: *(new option — `option/python/forbid_star_imports_option.py`)*
**Agent**: agent:rectifier-rules
**Bucket**: new-rule
**Severity**: feature

## Symptom
`from typing import *` and friends pollute the namespace, break tooling, and defeat both `RelocateImportsOption` and `RemoveUnusedOption` (they can't tell which symbols are actually used). Two real costs: discoverability (a reader can't tell where `Sequence` comes from) and refactor safety (a rename in the source module silently breaks the importer).

## Suggested direction
Phase 1 — **detect + warn**: LibCST visitor that scans `cst.ImportStar` occurrences and emits `target.io.warning(f"{path}: star import from {module}")`. Cheap, immediate value.

Phase 2 — **auto-resolve when safe**: when the imported module is statically importable (we can `importlib.import_module(module)` without side-effect — risky), enumerate its `__all__` and grep the file for which of those names are actually referenced. Replace the star with an explicit list. **Bail** on modules with side effects (any module under our `wexample_` or `syrtis_` prefix is generally side-effect-free for imports, but C-extension modules and third-party packages aren't).

Start with phase 1 only. Phase 2 is the "structural" version of this rule.
