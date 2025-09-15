from __future__ import annotations

import libcst as cst


def ensure_all_classes_docstring_first(module: cst.Module) -> cst.Module:
    """For each class in the module, ensure its docstring (if present) is first."""
    changed = False
    new_body = list(module.body)

    for i, node in enumerate(new_body):
        if isinstance(node, cst.ClassDef):
            if not is_class_docstring_first(node):
                updated = move_class_docstring_to_top(node)
                if updated is not node:
                    new_body[i] = updated
                    changed = True
    if not changed:
        return module
    return module.with_changes(body=new_body)


def find_class_docstring_nodes(
    classdef: cst.ClassDef,
) -> tuple[cst.SimpleStatementLine | None, int]:
    """Return (docstring_node, index) inside class body if present, else (None, -1).

    According to Python conventions, a class docstring is a first statement that's a
    string literal expression. We detect any top-level string literal in the class body.
    """
    body_elems = list(classdef.body.body)
    for i, elem in enumerate(body_elems):
        if isinstance(elem, cst.SimpleStatementLine) and len(elem.body) == 1:
            small = elem.body[0]
            if isinstance(small, cst.Expr) and isinstance(
                small.value, cst.SimpleString
            ):
                return elem, i
        # If we hit a non-simple line before finding a docstring, there's no docstring
        if not isinstance(elem, cst.SimpleStatementLine):
            break
    return None, -1


def is_class_docstring_first(classdef: cst.ClassDef) -> bool:
    node, idx = find_class_docstring_nodes(classdef)
    # Docstring is considered first if at index 0
    return node is not None and idx == 0


def move_class_docstring_to_top(classdef: cst.ClassDef) -> cst.ClassDef:
    """Move existing class docstring to be the first statement in the class body.

    Also normalizes quotes to double quotes and removes leading blank lines for the docstring.
    """
    doc, idx = find_class_docstring_nodes(classdef)
    if doc is None or idx == 0:
        return classdef

    normalized = normalize_docstring_quotes_stmt(doc).with_changes(leading_lines=[])

    body_list = list(classdef.body.body)
    body_list.pop(idx)
    body_list.insert(0, normalized)
    new_suite = classdef.body.with_changes(body=body_list)
    return classdef.with_changes(body=new_suite)


def normalize_docstring_quotes_stmt(
    stmt: cst.SimpleStatementLine,
) -> cst.SimpleStatementLine:
    """Normalize class docstring quotes to double quotes, similar to module behavior."""
    if not (isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1):
        return stmt
    small = stmt.body[0]
    if not (isinstance(small, cst.Expr) and isinstance(small.value, cst.SimpleString)):
        return stmt
    q = small.value.quote
    if q.startswith('"""') or q.startswith('"'):
        return stmt
    # Convert starting quote to double
    new_quote = '"""' if q.startswith("'''") else '"'
    new_value = small.value.with_changes(quote=new_quote)
    new_small = small.with_changes(value=new_value)
    return stmt.with_changes(body=[new_small])
