# New rule: flag mutable default arguments (warn-only, no auto-fix)

**Source**: *(new option — `option/python/flag_mutable_defaults_option.py`)*
**Agent**: agent:rectifier-rules
**Bucket**: new-rule
**Severity**: feature

## Symptom
Python's classic foot-gun: `def f(items=[]):` shares the same list across all calls. Same for `={}`, `=set()`, `=deque()`, attrs `default=[]`. Mypy/pyright don't catch it, ruff (rule `B006`) does — but we have no automated rectifier surfacing it in our sweep.

## Suggested direction
LibCST visitor over `cst.Param.default` that emits a `target.io.warning` (and optionally raises if the project is in strict mode) whenever the default expression is:
- `cst.List`, `cst.Dict`, `cst.Set` literal
- `cst.Call` whose func is `Name("list" | "dict" | "set")` with no args
- attrs `Factory(...)` is fine, but bare `=[]` inside `@attrs.define` is NOT fine

**Warn-only**. Auto-fix is dangerous: the safe replacement (`def f(items=None): items = items or []`) changes semantics if callers explicitly pass `None`. Leave the fix to humans; the rule's value is making the smell visible during rectification, not silently rewriting it.

References the existing `feedback_pas_de_defensif` philosophy: flag, don't paper over.
