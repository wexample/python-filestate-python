# _process_annotation creates bare Annotation, dropping original whitespace

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/unquote_annotations_option.py:52`
**Agent**: agent:performance
**Bucket**: restructure
**Severity**: bug

## Symptom
`cst.Annotation(annotation=expr)` constructs a fresh node with default whitespace, silently discarding the spacing the original annotation carried (e.g. the space after `:` in `x: "Foo"` may be normalised away).

## Suggested direction
Replace `cst.Annotation(annotation=expr)` with `ann.with_changes(annotation=expr)` so the existing whitespace fields are preserved; verify with a round-trip test that the colon-space is unchanged after unquoting.
