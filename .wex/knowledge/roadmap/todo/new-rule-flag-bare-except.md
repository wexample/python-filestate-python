# New rule: flag bare `except:` and `except Exception: pass` clauses

**Source**: *(new option — `option/python/flag_bare_except_option.py`)*
**Agent**: agent:rectifier-rules
**Bucket**: new-rule
**Severity**: feature

## Symptom
Two related smells:
1. `except:` (bare) — catches `KeyboardInterrupt`, `SystemExit`, everything. Almost always a bug.
2. `except Exception: pass` — silently eats every error, hiding bugs. Matches the project rule "Pas d'erreurs silencieuses".

## Suggested direction
LibCST visitor over `cst.ExceptHandler`:
- `handler.type is None` → bare except. Warn (severity: high). Auto-fix to `except Exception:` is debatable; safer to leave the rewrite to a human.
- `handler.type` is `cst.Name("Exception")` AND `handler.body` consists of a single `cst.Pass` → silent swallow. Warn (severity: high).

Warn-only (no auto-fix). The point is visibility during rectification, not silently changing semantics. References `feedback_no_silent_errors`.
