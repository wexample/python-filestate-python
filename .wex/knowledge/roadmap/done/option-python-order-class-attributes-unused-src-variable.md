# Unused `src` variable in `_apply_content_change`

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/order_class_attributes_option.py:31`
**Agent**: agent:performance
**Bucket**: style
**Severity**: style

## Symptom
`src, module = get_python_source_and_module(target)` unpacks two values but `src` is never referenced; only `module` is passed to `ensure_order_class_attributes_in_module`.

## Suggested direction
Replace the left-hand side with `_, module = ...` (or restructure `get_python_source_and_module` to have a module-only variant) to make the discard explicit and avoid confusion.

## Resolution
Applied the simple version: `_, module = get_python_source_and_module(target)`. Didn't restructure `get_python_source_and_module` — the source string is still relevant for other options sharing the cache, so a module-only variant would just duplicate the helper for one caller.
