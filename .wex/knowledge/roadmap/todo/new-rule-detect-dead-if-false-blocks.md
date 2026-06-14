# New rule: detect & remove dead `if False:` / `if 0:` blocks

**Source**: *(new option — `option/python/remove_dead_if_false_option.py`)*
**Agent**: agent:rectifier-rules
**Bucket**: new-rule
**Severity**: feature

## Symptom
Leftover debug branches:
```python
if False:
    foo_disabled_for_now()

if 0:
    print("trace")
```
…and their inverse: `if True:` blocks whose body should be hoisted out of the dead `if` wrapper. Trivially detectable; no semantic ambiguity.

## Suggested direction
LibCST `CSTTransformer` over `cst.If`:
- `test` is `cst.Name("False")` or `cst.Integer("0")` → remove the whole `If`, keep `orelse` (if any) hoisted into the parent body. **Bail if** there's an `elif` chain (`orelse` is itself an `If`), because hoisting needs careful handling — easier to skip.
- `test` is `cst.Name("True")` or `cst.Integer` with non-zero value → keep `body`, drop `orelse`. Hoist statements into parent body.

Cheap fast-path: scan once with a visitor, return early if no `False`/`0` / `True`/non-zero-int constant test found.

Out of scope: `if __debug__:` (controlled by `-O` flag, semantically meaningful), `if TYPE_CHECKING:` (handled elsewhere), `if 'X' in someset:` (not a literal).
