# Hoist nested `normalize` closure out of `_expected_class_name_from_path`

**Source**: `src/wexample_filestate_python/option/python/class_name_matches_file_name_option.py:34`
**Agent**: agent:performance
**Bucket**: restructure
**Severity**: perf

## Symptom
`normalize` is a pure function with no captured variables that is redefined as a new function object on every call to `_expected_class_name_from_path`, adding unnecessary per-call allocation overhead.

## Suggested direction
Move `normalize` to a module-level helper or a `@staticmethod` on the class so it is created once at import time rather than re-created on each invocation.

## Resolution
Promoted to `ClassNameMatchesFileNameOption._normalize_part` (`@staticmethod`). Kept the local `normalize = ClassNameMatchesFileNameOption._normalize_part` alias inside `_expected_class_name_from_path` so the comprehension reads the same way as before.
