# METADATA_NAMES: change tuple to frozenset for O(1) membership tests

**Source**: `packages/filestate-python/src/wexample_filestate_python/utils/python_module_metadata_utils.py:6`
**Agent**: agent:performance
**Bucket**: set-membership
**Severity**: perf

## Symptom
`METADATA_NAMES` is a `tuple[str, ...]` used exclusively for `in` membership tests (lines 137, 143). Tuple membership is O(n); frozenset is O(1).

## Suggested direction
Verify no caller iterates or indexes `METADATA_NAMES` by position, then change its type to `frozenset[str]` and update the annotation.

## Resolution
Grepped: both call sites use `in METADATA_NAMES` membership only — no iteration, no indexing. Migrated to `frozenset[str]` with the matching annotation.
