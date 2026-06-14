# Structural: tests must mirror source tree (every `src/x/y.py` → `tests/x/test_y.py`)

**Source**: *(new option — `option/python/test_mirror_source_tree_option.py`, package-level)*
**Agent**: agent:rectifier-design
**Bucket**: structural
**Severity**: feature

## Background
Standard Python testing convention: `src/foo/bar.py` ↔ `tests/foo/test_bar.py`. Without enforcement, the test tree drifts from the source tree over time — new modules ship without a paired test file, old test files outlive their source. Mostly harmless, but it hides coverage gaps and makes "where is `Foo` tested?" much harder than it should be.

This is a perfect fit for a filestate rule because filestate already owns the directory tree representation.

## Suggested direction
Package-level option:
1. Walk `src/<package>/` for every `.py` file except `__init__.py`, `_typing.py`, conftests, etc. (opt-out list configurable).
2. For each, derive the expected test path: `tests/<sub_path>/test_<basename>.py`.
3. Compare to actual files in `tests/`. Emit `target.io.warning(...)` for missing tests, and for orphan tests (test file referencing a removed source file — detectable via the file's `from src.x.y import ...` if any).

**No auto-fix in v1**. Generating an empty test scaffold automatically is tempting but produces noise (an empty `def test_TODO(): ...` is worse than no test). Phase 2 could template a real scaffold using the engram-style discovery from the orphan-module ticket: read the source's public API → generate a stub test per public function.

Composes with `agent:tests` referenced in the `project_ai_selection_engram` memory: same use case, different angle (gap detection vs. flakiness sweep).
