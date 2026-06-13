# `changed` flag not reset between class iterations in `reorder_flagged_constants_in_classes`

**Source**: `packages/filestate-python/src/wexample_filestate_python/utils/python_constants_utils.py:134`
**Agent**: agent:performance
**Bucket**: restructure
**Severity**: bug

## Symptom
`changed` is initialised once before the loop over all `ClassDef` nodes and never reset per class. Once a first class triggers a sort, `changed` stays `True` and subsequent unchanged classes still execute `node.body.with_changes(body=class_body_list)` unnecessarily, creating spurious CST node copies.

## Suggested direction
Move `changed = False` inside the `for idx, node` loop (reset per class) and apply the `with_changes` + body-update only when that class actually changed, avoiding redundant object creation for every subsequent class in the module.
