# Structural: shared idempotency fast-path hook for all options

**Source**: *(framework refactor — `option/python/abstract_python_file_content_option.py` + every concrete option)*
**Agent**: agent:rectifier-design
**Bucket**: structural
**Severity**: feature

## Background
Sibling perf ticket (`options-no-idempotency-early-exit-pattern.md`) catalogs ~8 options that lack a fast-path. The fix today would be a copy of the same boilerplate in each option:

```python
def _apply_content_change(self, target):
    src, module = get_python_source_and_module(target)
    if self._is_already_compliant(module):
        return src
    return self._do_transform(module).code
```

That's the natural shape — but pasting it 8× invites drift.

## Suggested direction
Reframe `AbstractPythonFileContentOption` (or a sibling abstract `AbstractCSTPythonOption`) so the standard contract is:
```python
@abstract_method
def _is_already_compliant(self, module: cst.Module) -> bool: ...

@abstract_method
def _transform(self, module: cst.Module) -> cst.Module: ...

# concrete (final) — provided by the abstract
def _apply_content_change(self, target) -> str:
    src, module = get_python_source_and_module(target)
    if self._is_already_compliant(module):
        return src
    return self._transform(module).code
```

Migrate per-file options one by one; non-CST options (FormatOption, FstringifyOption, RemoveUnusedOption) keep the current shape — they already short-circuit at the batch layer.

This also gives us a natural place to plug stats: count `compliant_hits` / `transformed_hits` per option per pass to identify which rectifiers are pulling weight on real-world projects.

Composes with the existing memory `project_tests_verts_passe_2026_06.md` — if we refactor the abstract, run the 793-test suite to confirm no regression.
