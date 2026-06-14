# class_name_matches_file_name: scope `NAME` but the option inspects file CONTENT

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/class_name_matches_file_name_option.py:20`
**Agent**: agent:rectifier-correctness
**Bucket**: scope-mismatch
**Severity**: bug

## Symptom
`get_scopes()` returns `[Scope.NAME]`, but `_class_name_matches_file_name` opens the file and parses its source with `ast.parse(...)` to look up a `ClassDef`. That is CONTENT work, not NAME work. Two consequences:
1. The scope filter in `AbstractItemTarget._prepare_options` will skip this option when only CONTENT is requested, even though the option *needs* the file contents.
2. When run under NAME scope, the option still reads disk, parses Python, and silently does nothing useful (because of the `print()` TODO — see sibling ticket).

The intent is probably: "the rule depends on CONTENT to compute the expected outcome, but the rectifying action targets the file NAME". Today the implementation conflates the two.

## Suggested direction
Declare both scopes — `return [Scope.NAME, Scope.CONTENT]` — so the option is included whenever either is in scope, OR split into two collaborating options (a content-side validator that emits a diagnostic, and a name-side rectifier that consumes it). Confirm against `_prepare_options` semantics that listing multiple scopes does not duplicate work.

## Resolution
Applied option 1: `get_scopes()` now returns `[Scope.NAME, Scope.CONTENT]`. Confirms the option needs CONTENT to read the class name from source and NAME because the eventual rectification (see sibling postponed ticket on the `print()` TODO) targets the file name.
