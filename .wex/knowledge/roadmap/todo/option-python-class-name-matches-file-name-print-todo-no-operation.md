# class_name_matches_file_name: `print()` TODO never produces an operation

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/class_name_matches_file_name_option.py:47`
**Agent**: agent:rectifier-correctness
**Bucket**: incomplete-implementation
**Severity**: bug

## Symptom
`create_required_operation` detects mismatch but only prints `" CORRECT {path}"` to stdout (with a stray leading space) and always returns `None`. No operation is ever created, no warning is surfaced via `target.io`, and `dry_run()` / `apply()` cannot report the rule as actionable. The rule is effectively dead today: the framework never proposes a rename, never raises a diagnostic, and the leftover `print` pollutes any CLI output that runs filestate.

## Suggested direction
Decide the intended behavior:
1. **Warn-only**: replace `print(...)` with `target.io.warning(...)` and return `None` consistently — the rule becomes a lint signal but never auto-rewrites.
2. **Rename operation**: build a `FileRenameOperation(target=target, new_name=<pascal_to_snake>(class_name) + ".py")` and return it so the framework actually rectifies, mirroring how `FixAttrsOption` returns the diff via the standard operation path.

Either way, remove the `# TODO` and the bare `print`. If option 2, also add a guard for files containing several classes (which one wins?) and for files that legitimately host a different-name class (e.g. mixins).
