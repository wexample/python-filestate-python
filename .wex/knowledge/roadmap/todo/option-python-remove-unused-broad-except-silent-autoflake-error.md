# remove_unused: bare `except Exception` swallows autoflake errors and returns source unchanged

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/remove_unused_option.py:30`
**Agent**: agent:rectifier-correctness
**Bucket**: defensive-swallow
**Severity**: bug

## Symptom
```python
try:
    return fix_code(src, remove_all_unused_imports=True, ...)
except Exception as e:
    target.io.error(f"Autoflake error: {e}\n\n")
    return src
```
Calling `target.io.error(...)` then returning `src` produces a non-blocking soft failure: nothing is raised, the rectifier reports "OK no change" for that file, and across a 268-file sweep the error scrolls past in the log and is forgotten. Worst case: autoflake breaks on a specific file (encoding issue, internal parse bug), the file silently stays full of unused imports, and the failure is invisible to CI.

The catch is also too broad — `Exception` covers programming bugs in our own callable wrapper, not just autoflake's documented failure mode.

## Suggested direction
- Drop the broad catch. Let exceptions propagate so the rectifier surfaces the offending file via the normal traceback path.
- If a real autoflake limitation must be tolerated (e.g. specific known patterns), narrow the catch to `autoflake.AutoflakeError` (or whichever concrete class autoflake exposes) and `raise FileStateBatchToolException(...)` so the framework treats it as a real failure.
- Mirrors the policy already documented in memory `feedback_no_silent_errors`.
