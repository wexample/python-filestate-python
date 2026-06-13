# toml_sort_string_array forces multiline instead of preserving it

**Source**: `src/wexample_filestate_python/helpers/toml.py:108`
**Bucket**: scope-unclear
**Severity**: bug

## Symptom
`toml_sort_string_array` does `multiline_flag = getattr(arr, "multiline", None)`, but
`multiline` is a bound method, so `multiline_flag` is always truthy. The later
`arr.multiline(multiline_flag)` then forces multiline=True on every sorted array,
turning single-line arrays into multiline ones despite the docstring promising the
existing style is preserved.

## Suggested direction
Detect the array's actual multiline state before re-appending (via tomlkit internals
such as the trivia/whitespace, not the method handle) and restore that exact flag.
