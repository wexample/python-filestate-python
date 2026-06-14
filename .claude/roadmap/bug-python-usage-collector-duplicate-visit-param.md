# Bug: duplicate `visit_Param` definition in PythonUsageCollector

**File:** `src/wexample_filestate_python/utils/relocate_imports/python_usage_collector.py`

## What

The class defines `visit_Param` **twice**:

1. Lines ~243–276 (first definition, returns `bool`):
   - Pushes `has_default` / `in_annot` booleans onto `_in_param_default_stack` /
     `_in_param_annot_stack`.
   - Records annotation types into `used_in_C_annot`.
   - Collects param-default identifiers into `used_in_B`.
   - Returns `True`.

2. Lines ~279–284 (second definition, returns `None`):
   - Only records annotation types into `used_in_C_annot`.
   - Does **not** manage any stacks / counters.
   - This definition **overwrites** the first in Python's class dict.

Because Python resolves attribute lookup in definition order, the second
`visit_Param` is the one that libcst's visitor dispatches to at runtime.
The entire first definition is **dead code**.

## Consequences

* Default-value names in function parameters were **not** reliably recorded into
  `used_in_B` via `visit_Param`. The `visit_Parameters` fallback (added with
  comment "some environments may not trigger visit_Param") inadvertently became
  the sole path for that logic.
* `leave_Param` stack-pop guards (`if self._in_param_default_stack: ...`) were
  always no-ops because nothing ever pushed to those stacks.

## Fix

After the 2026-06-14 performance pass, the boolean stacks were replaced with
integer counters (`_in_param_default_count`, `_in_param_annot_count`) and the
active `visit_Param` now increments them. The mirror decrement in `leave_Param`
is also in place.

**Remaining work:**

1. Delete the dead first `visit_Param` definition (lines ~243–276).
2. Merge its param-default collection logic (the `_collect_base_names` inner
   function) into the active `visit_Param` so the `visit_Parameters` fallback
   becomes truly optional.
3. Verify that `visit_Parameters` can then be removed or left as a safety net
   with an updated comment.
4. Add a regression test: a parameter with a default that references an imported
   name should appear in `used_in_B`.
