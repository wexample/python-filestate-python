# visit_Attribute: isinstance guard is always true per libcst type contract

**Source**: `packages/filestate-python/src/wexample_filestate_python/utils/relocate_imports/python_usage_collector.py:133`
**Agent**: agent:performance
**Bucket**: redundant-check
**Severity**: perf

## Symptom
`if isinstance(node.value, cst.BaseExpression):` guards the recursive visit in `visit_Attribute`. In libcst, `Attribute.value` is statically typed as `BaseExpression`, so this isinstance call always returns True, adding an unnecessary type check on every attribute node visited.

## Suggested direction
Remove the isinstance guard and call `node.value.visit(self)` unconditionally; confirm with a quick grep of libcst's `Attribute` dataclass definition that the type annotation is non-union.
