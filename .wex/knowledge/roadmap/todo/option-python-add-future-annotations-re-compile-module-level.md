# Hoist re.compile to module level in _apply_content_change

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/add_future_annotations_option.py:36`
**Agent**: agent:performance
**Bucket**: restructure
**Severity**: perf

## Symptom
`re.compile(r"^#.*coding[:=]\s*([-_.a-zA-Z0-9]+)")` is called inside `_apply_content_change` on every invocation, recompiling the pattern each time even though it is a constant.

## Suggested direction
Move the compiled pattern to module-level (or class-level) so it is compiled once at import time and reused across all calls.
