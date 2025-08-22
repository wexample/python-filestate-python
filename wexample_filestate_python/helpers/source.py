from __future__ import annotations

import ast


def source_infer_simple_return_type(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str | None:
    """Deprecated helper kept for backwards compatibility. Logic moved into
    PythonAddReturnTypesOperation.preview_source_change."""
    # Minimal shim: preserve old behavior by re-implementing quickly
    returns: list[ast.Return] = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
    if not returns:
        return "None"
    kinds: set[str] = set()
    for ret in returns:
        val = ret.value
        if val is None:
            kinds.add("None")
        elif isinstance(val, ast.Constant):
            if isinstance(val.value, bool):
                kinds.add("bool")
            elif isinstance(val.value, str):
                kinds.add("str")
            elif isinstance(val.value, int):
                kinds.add("int")
            elif isinstance(val.value, float):
                kinds.add("float")
            elif val.value is None:
                kinds.add("None")
            else:
                return None
        else:
            return None
    if len(kinds) == 1:
        return next(iter(kinds))
    return None


def source_remove_future_imports(src: str) -> str:
    """Return source with top-level `from __future__ import ...` statements removed.

    Handles multi-line imports using AST node span (lineno/end_lineno).
    If parsing fails for any reason, returns the original source.
    """
    import ast

    tree = ast.parse(src)

    # Collect (start_line, end_line) ranges (0-based, inclusive) for future-imports
    spans: list[tuple[int, int]] = []
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            # end_lineno is available in 3.8+
            start = max(0, (node.lineno - 1))
            end = max(start, (getattr(node, "end_lineno", node.lineno) - 1))
            spans.append((start, end))

    if not spans:
        return src

    # Merge overlapping spans just in case
    spans.sort()
    merged: list[tuple[int, int]] = []
    for s, e in spans:
        if not merged or s > merged[-1][1] + 1:
            merged.append((s, e))
        else:
            ms, me = merged[-1]
            merged[-1] = (ms, max(me, e))

    lines = src.splitlines(keepends=True)
    keep: list[str] = []
    i = 0
    mi = 0
    while i < len(lines):
        if mi < len(merged):
            s, e = merged[mi]
            if s <= i <= e:
                # skip this line in span
                i = e + 1
                mi += 1
                # Also remove an immediate trailing blank line if present to avoid double newlines
                if i < len(lines) and lines[i].strip() == "":
                    i += 1
                continue
        keep.append(lines[i])
        i += 1

    return "".join(keep)
