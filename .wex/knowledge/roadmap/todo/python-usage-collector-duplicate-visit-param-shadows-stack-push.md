# Duplicate visit_Param: second definition shadows the first, stacks never pushed

**Source**: `packages/filestate-python/src/wexample_filestate_python/utils/relocate_imports/python_usage_collector.py:247,283`
**Agent**: agent:performance
**Bucket**: restructure
**Severity**: bug

## Symptom
`PythonUsageCollector` defines `visit_Param` twice. Python silently keeps only the second definition (line 283), which only records annotation names. The first definition (line 247), which pushes to `_in_param_default_stack` and `_in_param_annot_stack`, is never called. `leave_Param` (line 70) therefore pops stacks that were never pushed, and `visit_Name` reads from stacks that are always empty, so param-default and param-annotation guard flags never activate.

## Suggested direction
Merge both `visit_Param` bodies into a single method and return `True` to keep child traversal; remove the dead second definition and verify the stacks are correctly balanced by the corresponding `leave_Param`.
