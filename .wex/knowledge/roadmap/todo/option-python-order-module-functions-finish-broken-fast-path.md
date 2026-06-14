# order_module_functions: complete the broken fast-path that just `pass`es

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/order_module_functions_option.py:36`
**Agent**: agent:performance
**Bucket**: idempotency-fast-path
**Severity**: perf

## Symptom
A sibling ticket (`option-python-order-module-functions-dead-noop-check.md`) already flagged that the `if module_functions_sorted_before_classes(module): pass` block is dead. This ticket is the **finish-the-job** companion: actually wire up the fast-path the comment promised — check sort order *and* alpha/visibility — and early-return `src` when the module is already compliant.

## Suggested direction
Add a `module_functions_already_ordered(module) -> bool` helper in `python_functions_utils.py` that checks:
1. All function defs come before any class def (already what `module_functions_sorted_before_classes` returns).
2. Within the function block, the order is: public (alpha) → private/`_*` (alpha).
3. `@overload` groups are contiguous with their implementation.

In the option, replace the `if ...: pass` with `if module_functions_already_ordered(module): return src`. This converts the existing dead traversal into an actual win.
