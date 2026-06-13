# toml_ensure_table reports changed=True for an existing but empty table

**Source**: `src/wexample_filestate_python/helpers/toml.py:52`
**Bucket**: scope-unclear
**Severity**: bug

## Symptom
The guard `if not tbl or not isinstance(tbl, dict)` treats an existing but empty tomlkit
table as missing (empty tables are falsy), so it recreates the table and returns
changed=True even though nothing actually changed. Callers using the changed flag to
decide whether to rewrite a file will rewrite needlessly.

## Suggested direction
Distinguish "missing" from "present but empty": use `tbl is None or not isinstance(tbl, dict)`
instead of `not tbl`. Verify no caller relies on empty tables being re-created.
