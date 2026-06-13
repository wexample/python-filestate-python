# visit_Parameters: ternary expression result is silently discarded (dead code)

**Source**: `packages/filestate-python/src/wexample_filestate_python/utils/relocate_imports/python_usage_collector.py:290`
**Agent**: agent:performance
**Bucket**: restructure
**Severity**: style

## Symptom
`self.func_stack[-1] if self.func_stack else "<module>"` is evaluated but its result is never assigned or used. This incurs a needless list-index (or string literal) at every `visit_Parameters` call with no observable effect.

## Suggested direction
Either assign the result to a variable and use it in subsequent logic, or remove the dead expression entirely if it was left over from a debug pass.
