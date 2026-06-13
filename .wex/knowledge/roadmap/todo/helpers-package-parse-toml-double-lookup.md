# package_parse_toml: double hash-lookup on "project" key

**Source**: `packages/filestate-python/src/wexample_filestate_python/helpers/package.py:118`
**Agent**: agent:performance
**Bucket**: dict-get
**Severity**: perf

## Symptom
`if "project" in data:` followed by `data["project"]` performs two hash-table lookups for the same key on every call.

## Suggested direction
Replace with `project_data = data.get("project")` + `if project_data:`, but verify the empty-dict edge case: the current code returns `{"name": None, "install_requires": []}` when `data["project"] == {}`, whereas the simplified form would return `{}` — confirm callers handle both shapes uniformly before applying.
