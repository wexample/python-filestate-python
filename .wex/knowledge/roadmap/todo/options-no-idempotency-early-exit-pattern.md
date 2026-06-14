# Several options have no idempotency early-exit, paying parse + render on every pass

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/{fix_blank_lines_option.py, fix_attrs_option.py, order_class_attributes_option.py, order_class_methods_option.py, sort_imports_option.py, remove_unused_option.py, unquote_annotations_option.py, add_return_types_option.py}`
**Agent**: agent:performance
**Bucket**: idempotency-fast-path
**Severity**: perf

## Symptom
The framework only detects "no change needed" *after* an option has fully produced its candidate output: the parsed module is mutated, `.code` re-renders it to text, and `_create_write_operation_if_content_changed` compares the rendered string to the disk content. For options listed above, the implementation does parse → transform → render unconditionally — no per-option fast path.

A handful of siblings already do it right:
- `OrderMainGuardOption` short-circuits when `is_main_guard_at_end(module)` is true.
- `OrderModuleMetadataOption` checks contiguity + sort + position before rebuilding.
- `OrderTypeCheckingBlockOption` exits when blocks are already at the right index.
- `OrderModuleDocstringOption` exits when docstring is already first and quoted correctly.

Across a 268-file sweep × ~20 options per file, the unnecessary render cost compounds. Parsing is already cached via `cst_cache`, so the main saving is the per-option render (`module.code`) and the per-option visitor pass.

## Suggested direction
For each option in the list, add a cheap `_is_already_compliant(module) -> bool` check before the transformation. Pattern is consistent with `OrderModuleMetadataOption` — a single visitor that walks the relevant subtree, returns early on first mismatch. Track which options actually benefit (measure render time on a real sweep) and skip the ones whose check would cost as much as the transform itself (e.g. `UnquoteAnnotationsOption` — the check IS the transform).
