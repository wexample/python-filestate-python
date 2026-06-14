# New rule: normalize `== None` / `!= None` → `is None` / `is not None`

**Source**: *(new option — `option/python/normalize_none_equality_option.py`)*
**Agent**: agent:rectifier-rules
**Bucket**: new-rule
**Severity**: feature

## Symptom
PEP 8: comparisons to `None` must use identity (`is`), not equality (`==`). Easy to slip up, especially in code translated from other languages. Ruff catches it (`E711`); we can both fix it automatically.

## Suggested direction
LibCST `CSTTransformer` over `cst.Comparison` nodes:
- If `left` or any operand is `cst.Name("None")` AND the operator is `cst.Equal()` / `cst.NotEqual()`, rewrite to `cst.Is()` / `cst.IsNot()`.
- Preserve whitespace via `.with_changes(...)`.

Also covers `== True` / `== False` / `is True` / `is False` → either rewrite to bare boolean expressions or leave alone (riskier, since `is True` and `bool(x)` differ on truthy non-bool values — make that a separate **opt-in** rule with a flag, not the default).

Fully idempotent: re-running over an already-rectified file produces zero changes (no `==`/`!=` against `None` to find).
