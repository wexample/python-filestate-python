# Performance: hoist deferred import in OrderIterableItemsOption

**File:** `src/wexample_filestate_python/option/python/order_iterable_items_option.py`

**What:** `_apply_content_change` contains a deferred `from … import reorder_flagged_iterables`
inside the method body. Python's import machinery still performs a `sys.modules` dict lookup
+ package-attribute traversal on every call, even though the module is cached.

Moving the import to module level:

```python
from wexample_filestate_python.utils.python_iterable_utils import reorder_flagged_iterables
```

…would pay that cost exactly once at module load time.

**Blocker before applying:** Verify there is no circular import between
`wexample_filestate_python.option.python.order_iterable_items_option` and
`wexample_filestate_python.utils.python_iterable_utils`. The utils module itself uses a
deferred import of `wexample_filestate.helpers.flag` (a cross-package dependency), suggesting
the lazy-import style may be a project-wide convention for circular-import avoidance. Trace the
full import graph before promoting this import to module scope.

**Expected gain:** Eliminates 1–3 attribute lookups per `_apply_content_change` call. Minor
in absolute terms but consistent with the intra-method micro-optimisation mandate.
