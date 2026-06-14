# class_name_matches_file_name: `print()` TODO never produces an operation

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/class_name_matches_file_name_option.py:47`
**Agent**: agent:rectifier-correctness
**Bucket**: incomplete-implementation
**Severity**: bug
**Status**: postponed — depends on cross-file rename propagation design

## Symptom
`create_required_operation` detects mismatch but only prints `" CORRECT {path}"` to stdout (with a stray leading space) and always returns `None`. No operation is ever created, no warning is surfaced via `target.io`, and `dry_run()` / `apply()` cannot report the rule as actionable. The rule is effectively dead today: the framework never proposes a rename, never raises a diagnostic, and the leftover `print` pollutes any CLI output that runs filestate.

## Why postponed
Fixing the `print` is the easy part. The hard part is what the option should actually do, and that opens two unsolved questions:

1. **Direction of the rename** — file → class, or class → file? Neither answer is universally right. A scaffolded-from-template class probably wants its class renamed to match the (intentional) file name; a refactor that renamed the class probably wants the file renamed to follow. The rectifier cannot pick the direction by inspecting the file alone; it needs project-level intent (a flag, a convention scope, or a marker comment).

2. **Cross-file propagation** — whichever side we rename (`Foo` → `Bar`, or `foo.py` → `bar.py`), every importer in the codebase must be updated atomically. A rename without propagation produces a broken tree on disk between two `apply()` passes. This is **the** mechanism the user wants to validate via the event package (`PACKAGES/PYTHON/packages/event/src/wexample_event/`) — operations emit events (`OperationCompleted`, `SymbolRenamed`, etc.), and listeners (other options, an import-rewriter pass, an engram-style cross-file index) react to keep the project consistent.

Until both questions are answered — and especially until the event-driven propagation pattern is prototyped end-to-end on a smaller rename use case — wiring up a `FileRenameOperation` here would create more breakage than it fixes.

## Suggested direction
Two things to defer:
1. **Decide the rename direction** — likely via a new option flag (`prefer: "class" | "file"`) plus a per-target override, with sensible defaults documented per workdir type.
2. **Validate the event mechanism** — pick a simpler rename rectifier first (e.g. a renamed module symbol with a known set of importers), prototype the `OperationCompleted` → propagation pipeline using the `wexample_event` package, and only then come back here to wire this option onto the proven event flow.

Short-term mitigation (cheap, harmless): replace the bare `print(f" CORRECT {target.get_path()}")` with `target.io.warning(...)` so existing detections at least surface cleanly while the structural design is in flight.

## Related
- [[structural-cross-file-orphan-module-detector]] — same need for a cross-file import index.
- `PACKAGES/PYTHON/packages/event/src/wexample_event/` — the event package whose `Operation*` lifecycle we want to validate here.
