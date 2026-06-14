# add_return_types: duplicate "infer class-call type" logic across collector and transformer

**Source**: `packages/filestate-python/src/wexample_filestate_python/option/python/add_return_types_option.py:96,142`
**Agent**: agent:rectifier-correctness
**Bucket**: restructure
**Severity**: style

## Symptom
The class-call type inference is duplicated:
- `_FunctionAssignCollector._infer_call_type` (≈ line 96) inspects `call.func` for `Name` / `Attribute`, checks `func.value in self.known_types`, applies the uppercase-first-letter heuristic.
- `AddReturnTypesTransformer._infer_return_expr_type` (≈ line 142) reproduces the exact same `Name` + `Attribute` + known-types + uppercase logic against `expr` when it is a `cst.Call`.

Any future refinement (handling generics, qualified module paths, subscripted calls, etc.) has to be added in both places. The risk of drift is the typical "two-truths" bug.

## Suggested direction
Extract a module-private helper `def _infer_class_call_type(call: cst.Call, known_types: set[str]) -> str | None:` and have both call sites delegate. Keep it `@staticmethod` if any, or a plain function. No behavior change expected — just one source of truth.
