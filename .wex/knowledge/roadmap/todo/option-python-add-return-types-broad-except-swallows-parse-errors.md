# add_return_types: bare `except Exception` swallows parse errors silently

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/add_return_types_option.py:29`
**Agent**: agent:rectifier-correctness
**Bucket**: defensive-swallow
**Severity**: bug

## Symptom
```python
try:
    src, module = get_python_source_and_module(target)
except Exception:
    return target.get_local_file().read()
```
Any failure during the cached parse (libcst syntax error, OS error, unicode decode error, even an unrelated bug somewhere in the cst_cache helper) is silently swallowed and the file is returned unchanged. No log, no warning, no propagation. This conflicts with the project rule "Pas d'erreurs silencieuses" — and worse, it hides genuine parse regressions across the whole sweep because every other CST option also uses `get_python_source_and_module`.

## Suggested direction
Drop the try/except entirely: let the exception bubble. If a few legitimate cases really need to be tolerated (e.g. genuinely unparseable Python 2 files), narrow the catch to `cst.ParserSyntaxError` and emit `target.io.warning(f"add_return_types: skipped {path} — parse error: {e}")` so the user sees what was skipped and why. Never catch bare `Exception`.
