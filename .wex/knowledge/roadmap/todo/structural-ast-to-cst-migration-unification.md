# Structural: migrate remaining `ast.parse` options to libcst via `cst_cache`

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/{add_future_annotations_option.py, class_name_matches_file_name_option.py}`
**Agent**: agent:rectifier-design
**Bucket**: structural
**Severity**: enhancement

## Background
Two options still use stdlib `ast` instead of libcst:
- `AddFutureAnnotationsOption` — parses with `ast` to find module docstring, then string-manipulates `lines`. Loses whitespace fidelity, can't share the `cst_cache`.
- `ClassNameMatchesFileNameOption` — parses with `ast.parse` for read-only ClassDef lookup.

Every other option already shares a single libcst parse via `get_python_source_and_module(target)`. The two stragglers double-parse the same file. On a 268-file sweep, that's 268 extra `ast.parse` calls — small in absolute terms (`ast.parse` is C-fast) but a needless duplication of the parsed representation.

More importantly: if `add_future_annotations` ever needs to inspect *more* than just the docstring (e.g. "is there already a `from __future__ import X` but missing `annotations`?"), the string-based heuristic will break, while a CST-based one would handle it naturally.

## Suggested direction
1. **AddFutureAnnotationsOption** — rewrite using `cst_cache` + a small visitor that locates the insertion point (after shebang comment lines + after the module docstring) and uses `module.with_changes(body=[future_import] + module.body)` style. Black or our `fix_blank_lines` will normalize the blank-line afterwards.
2. **ClassNameMatchesFileNameOption** — replace `ast.parse(source)` with the cached libcst module; iterate `module.body` for `cst.ClassDef`. No behavioral change; only memory + parse savings.

Optionally: drop the `import ast` in `abstract_python_file_content_option.py`'s dep graph once nothing in `option/python/` uses it.
