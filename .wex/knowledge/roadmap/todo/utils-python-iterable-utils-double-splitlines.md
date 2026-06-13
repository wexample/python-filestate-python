# Double splitlines() call in reorder_flagged_iterables

**Source**: `packages/filestate-python/src/wexample_filestate_python/utils/python_iterable_utils.py:17`
**Agent**: agent:performance
**Bucket**: restructure
**Severity**: perf

## Symptom
`reorder_flagged_iterables` calls `src.splitlines()` at line 17, then `_find_flag_line_indices` calls `src.splitlines()` again internally at line 126, splitting the same string twice on every invocation.

## Suggested direction
Accept an already-split `lines: list[str]` parameter in `_find_flag_line_indices` (or inline the flag search into `reorder_flagged_iterables`) so the string is split only once.
