# module_functions_sorted_before_classes traverses module.body twice

**Source**: `packages/filestate-python/src/wexample_filestate_python/utils/python_functions_utils.py:49`
**Agent**: agent:performance
**Bucket**: restructure
**Severity**: perf

## Symptom
`module_functions_sorted_before_classes` iterates `module.body` in two separate loops: once to find the first `ClassDef` (line 49) and again from the beginning to find the first `FunctionDef` (line 56). On large modules both indices could be found in a single pass.

## Suggested direction
Merge into one loop that tracks both `first_class_index` and `first_func_index`, breaking early once both are found.
