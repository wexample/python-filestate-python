# package_parse_setup uses ast.Str, removed in Python 3.14

**Source**: `src/wexample_filestate_python/helpers/package.py:97`
**Bucket**: scope-unclear
**Severity**: bug

## Symptom
`package_parse_setup` relies on `ast.Str` and the `.s` attribute, both deprecated since
Python 3.8 and scheduled for removal in 3.14. It currently works (with DeprecationWarning)
on 3.12 but will raise on 3.14, breaking setup.py metadata parsing.

## Suggested direction
Switch to `ast.Constant` with `isinstance(node.value, str)` checks and read `node.value`
instead of `node.s`, mirroring the same change for the list-element branch.
