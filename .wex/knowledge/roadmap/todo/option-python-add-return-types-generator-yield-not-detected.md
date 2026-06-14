# add_return_types: generators (functions with `yield`) wrongly annotated `-> None`

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/add_return_types_option.py:218`
**Agent**: agent:rectifier-correctness
**Bucket**: type-inference-bug
**Severity**: bug

## Symptom
`_infer_for_function` collects `cst.Return` nodes only. A generator like

```python
def stream_items():
    for i in items:
        yield i
```

has zero `return` nodes, so `_ReturnCollector.returns` is empty and the inferred type becomes `"None"`. The rectifier then writes `def stream_items() -> None:` — a false annotation that mypy/pyright will flag (a generator is `Iterator[X]` / `Generator[X, ..., ...]`, never `None`).

## Suggested direction
Extend `_ReturnCollector` to also record any `cst.Yield` / `cst.YieldFrom` it encounters at the same nesting level. If any yield is found, **bail** (return `None` from the inference, leaving the function unannotated) — proper `Iterator[X]` inference is out of scope for the simple-types pass and would need to peek into yielded expressions. Add a regression test on a tiny generator and a `yield from` case.
