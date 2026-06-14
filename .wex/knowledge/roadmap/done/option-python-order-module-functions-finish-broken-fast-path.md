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

## Resolution
Added `module_functions_already_ordered(module) -> bool` in `python_functions_utils.py`. It delegates to `module_functions_sorted_before_classes` for the function-before-class check, then collects function groups via `collect_module_function_groups` and compares their names to the canonical order produced by `sort_function_groups`. Overload contiguity is enforced implicitly: a non-contiguous overload chain would split into multiple single-name groups and fail the name comparison.

In `order_module_functions_option.py`, the dead `if ...: pass` block is gone, replaced by `if module_functions_already_ordered(module): return src`. Closes both this ticket and its sibling `option-python-order-module-functions-dead-noop-check.md` (the pre-existing one that flagged the dead block).
