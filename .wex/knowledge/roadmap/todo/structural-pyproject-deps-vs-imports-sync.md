# Structural: sync `pyproject.toml` declared deps with actual imports (à la deptry)

**Source**: *(new option — `option/python/check_pyproject_deps_option.py`)*
**Agent**: agent:rectifier-design
**Bucket**: structural
**Severity**: feature

## Background
Two recurring frictions in wex packages:
- **Unused declared deps**: `pyproject.toml` lists `requests` but no file actually imports it. Bloats install, slows CI, hides historical refactor leftovers.
- **Undeclared imports**: a file does `import foobar` but `foobar` is not in `dependencies` — it works locally because it was installed as a transitive of something else, but it breaks the moment that transitive dep is updated to a version that no longer pulls `foobar`.

External tools (`deptry`, `pip-check-reqs`) solve this but live outside our rectification flow. Integrating it as a filestate option means the check runs on every `wex app::start`, not just CI.

## Suggested direction
Package-level option (same shape as the orphan-module ticket). Workflow:
1. Parse `pyproject.toml` once at the package root — extract `[project.dependencies]` + `[project.optional-dependencies.*]`. Build a set of declared distribution names. Map them to their actual top-level import name(s) via `importlib.metadata` — `pyyaml` provides `yaml`, `pillow` provides `PIL`, etc. The mapping is the tricky part; cache it once at startup.
2. Walk every `.py` file (reuse the cst_cache). For each `import` / `from`, extract the root module name. Skip names that resolve to the current package itself, to stdlib, or to relative imports.
3. Compare:
   - `imported - declared_after_mapping` → undeclared.
   - `declared_after_mapping - imported` → declared-but-unused. Bail on names known to be "side-effect-only" deps (e.g. `python-dotenv`, packaging plugins, type stubs) — keep an opt-out list in the option's config.
4. Emit `target.io.warning(...)` per category.

Reference: `feedback_packagist_versions_stale` shows the same class of bug on the PHP side — divergence between declared and actually-used deps causes real production breakage. Same risk applies here.

Out of scope of v1: auto-rewrite `pyproject.toml` to add the missing deps. Listing them is enough — the human picks the right version.
