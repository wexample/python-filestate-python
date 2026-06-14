# Structural: cross-file orphan-module detector

**Source**: *(new option — `option/python/detect_orphan_modules_option.py` + package-level visitor)*
**Agent**: agent:rectifier-design
**Bucket**: structural
**Severity**: feature

## Background
Today every option works on a single file. The biggest dead-code wins (unused imports inside a file) already exist via autoflake. The biggest unfound category is unused **files** — modules that nobody imports anywhere in the package. They survive every per-file pass and accumulate over years.

## Suggested direction
Promote this rule to a **package-level** option (a new abstract shape, since current options are per-file). At the start of the rectification pass:

1. Walk every `.py` file under the package root once. Parse with libcst (use the existing `cst_cache`). For each, collect the set of imported names: `from pkg.mod import X` → record `pkg.mod` + `pkg.mod.X`.
2. Build a reverse index: for each module path in the package, which files import from it?
3. Modules imported by zero files (except their parent `__init__.py` re-exports and `tests/`) are orphans.

Output: a single report at the end (`target.io.warning(f"Orphan modules: ...")`) — never auto-delete (too risky cross-monorepo, hidden import via string, plugin-style discovery, etc.).

**Pre-requisites**:
- A new abstract `WithPackageScopeOption` mixin that runs once at package level, not per-file. Could share infrastructure with `WithBatchOptionMixin` — both already "run once across many files". See the `structural-shared-idempotency-fast-path-hook.md` ticket for the broader refactor angle.
- Honor exclusions: `__init__.py`, `tests/`, CLI entry points listed in `pyproject.toml [project.scripts]`, `conftest.py`.

This connects to the "Selection + Engram" memory: an engram-style cross-file index is exactly what this rule needs, and it'd unlock several other rules (renamed-class detector, deduplicate-protocol detector, dependency-graph-cycle detector).
