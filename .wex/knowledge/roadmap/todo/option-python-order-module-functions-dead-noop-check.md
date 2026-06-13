# Dead no-op check wastes a full module traversal on every call

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/order_module_functions_option.py:36`
**Agent**: agent:performance
**Bucket**: benchmark-first
**Severity**: perf

## Symptom
`module_functions_sorted_before_classes(module)` is called inside `_apply_content_change` but its return value is immediately discarded (`if ...: pass`). The comment says this was intended as a quick no-op detection / early-return guard, but the guard was never completed. Every call pays the traversal cost of the check with zero benefit.

## Suggested direction
Either complete the early-return path (`if module_functions_sorted_before_classes(module) and <alpha+visibility already sorted>: return src`) or remove the dead block entirely after confirming the function has no side effects.
