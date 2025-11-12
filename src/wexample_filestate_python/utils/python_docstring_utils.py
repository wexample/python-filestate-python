from __future__ import annotations

from typing import TYPE_CHECKING

import libcst as cst

if TYPE_CHECKING:
    pass


def find_module_docstring(
    module: cst.Module,
) -> tuple[cst.SimpleStatementLine | None, int]:
    """Find the module docstring in a CST module.

    Args:
        module: The CST module to search

    Returns:
        A tuple of (docstring_node, position) where position is the index
        in module.body. Returns (None, -1) if no docstring found.
    """
    for i, stmt in enumerate(module.body):
        # Skip comments and blank lines at the start
        if isinstance(stmt, (cst.SimpleStatementLine)):
            if len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr):
                expr = stmt.body[0]
                if isinstance(expr.value, cst.SimpleString):
                    # This is a string literal at module level - likely a docstring
                    return stmt, i
        elif not isinstance(stmt, cst.SimpleStatementLine):
            # Hit a non-simple statement (like import, class, def) - no docstring
            break

    return None, -1


def is_module_docstring_at_top(module: cst.Module) -> bool:
    """Check if the module docstring is already at the top position.

    Args:
        module: The CST module to check

    Returns:
        True if docstring is at position 0, False otherwise
    """
    docstring_node, position = find_module_docstring(module)
    return docstring_node is not None and position == 0


def move_docstring_to_top(module: cst.Module) -> cst.Module:
    """Move the module docstring to the top of the file.

    Args:
        module: The CST module to modify

    Returns:
        Modified module with docstring at the top
    """
    docstring_node, position = find_module_docstring(module)

    if docstring_node is None or position == 0:
        # No docstring or already at top
        return module

    # Normalize quotes in the docstring
    normalized_docstring = normalize_docstring_quotes(docstring_node)

    # Remove docstring from current position
    new_body = list(module.body)
    new_body.pop(position)

    # Insert at the beginning with no leading whitespace
    # Ensure the docstring has no leading newlines
    clean_docstring = normalized_docstring.with_changes(leading_lines=[])

    new_body.insert(0, clean_docstring)

    return module.with_changes(body=new_body)


def normalize_docstring_quotes(
    docstring_node: cst.SimpleStatementLine,
) -> cst.SimpleStatementLine:
    """Convert single quotes to double quotes in docstring nodes.

    Args:
        docstring_node: A CST node containing a docstring statement

    Returns:
        The same node with normalized double quotes
    """
    if not isinstance(docstring_node.body[0], cst.Expr):
        return docstring_node

    expr = docstring_node.body[0]
    if not isinstance(expr.value, cst.SimpleString):
        return docstring_node

    string_value = expr.value
    quote = string_value.quote

    # Convert single quotes to double quotes
    if quote.startswith("'''"):
        new_quote = '"""'
    elif quote.startswith("'"):
        new_quote = '"'
    else:
        # Already using double quotes
        return docstring_node

    # Create new string with double quotes
    new_string = string_value.with_changes(quote=new_quote)
    new_expr = expr.with_changes(value=new_string)
    new_body = [new_expr] + list(docstring_node.body[1:])

    return docstring_node.with_changes(body=new_body)
