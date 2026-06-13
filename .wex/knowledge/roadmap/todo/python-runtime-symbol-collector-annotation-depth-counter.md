# Replace in_annotation_stack list with an int depth counter

**Source**: `packages/filestate-python/src/wexample_filestate_python/utils/relocate_imports/python_runtime_symbol_collector.py:17`
**Agent**: agent:performance
**Bucket**: restructure
**Severity**: perf

## Symptom
`in_annotation_stack` is a `list[bool]` used solely as a nesting depth flag: `append(True)` on enter, `pop()` on leave, and truthiness check when visiting. A plain `int` counter avoids list allocation and object churn.

## Suggested direction
Replace `in_annotation_stack: list[bool]` with `_annotation_depth: int = 0`; increment on `visit_Annotation`, decrement on `leave_Annotation`, and test with `if self._annotation_depth:`.
