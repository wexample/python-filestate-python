# New rule: suggest `@staticmethod` for instance methods that never use `self`

**Source**: *(new option — `option/python/suggest_staticmethod_option.py`)*
**Agent**: agent:rectifier-rules
**Bucket**: new-rule
**Severity**: feature

## Symptom
Methods declared as `def foo(self, x)` that never touch `self` should be `@staticmethod` (or sometimes module-level functions). Mypy/pyright don't flag this; ruff (`PLR6301`) does but as an info-level rule that nobody enables. We have many such cases in the codebase — easy to spot, slight clarity win, and matches the existing `OrderClassMethodsOption` taxonomy (staticmethods sort separately).

## Suggested direction
LibCST visitor:
1. For each `FunctionDef` directly inside a `ClassDef`, with no `@staticmethod` / `@classmethod` / `@property` decorator and `params.params[0].name.value == "self"`:
2. Walk the body, count `cst.Name("self")` references AND `cst.Attribute(value=Name("self"))` references. (Both count — `self` itself appearing in `lambda x: self` for example.)
3. If zero references: emit `target.io.warning(...)` and (optionally) auto-add `@staticmethod` + remove the `self` parameter.

**Bail on**:
- Decorated methods (could be intercepted).
- Methods inheriting from a parent that expects the signature (impossible to verify cross-file without engram-style analysis — see structural ticket).
- Dunder methods.

Warn-only by default; auto-fix behind an opt-in flag because of the inheritance trap.
