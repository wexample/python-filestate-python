from __future__ import annotations

from typing import List

import libcst as cst


def _is_blank_line(node: cst.CSTNode) -> bool:
    """Return True if node is an EmptyLine without a comment (blank line)."""
    return isinstance(node, cst.EmptyLine) and node.comment is None


def _remove_leading_blank_lines_from_suite(suite: cst.Suite) -> cst.Suite:
    """Remove any leading blank lines from a function/method body suite.
    
    This ensures no blank lines appear immediately after the function signature,
    whether there's a docstring or not.
    """
    body_list = list(suite.body)
    if not body_list:
        return suite
    
    changed = False
    
    # Check first element for leading_lines with blank lines
    if body_list and isinstance(body_list[0], cst.SimpleStatementLine):
        first_stmt = body_list[0]
        if first_stmt.leading_lines:
            # Remove blank leading lines from the first statement
            new_leading = [line for line in first_stmt.leading_lines if not (isinstance(line, cst.EmptyLine) and line.comment is None)]
            if len(new_leading) != len(first_stmt.leading_lines):
                body_list[0] = first_stmt.with_changes(leading_lines=new_leading)
                changed = True
    
    # Remove leading blank EmptyLine nodes
    while body_list and _is_blank_line(body_list[0]):
        body_list.pop(0)
        changed = True
    
    # If first statement is a docstring, ensure no blank lines after it
    if body_list and isinstance(body_list[0], cst.SimpleStatementLine):
        first_stmt = body_list[0]
        if (len(first_stmt.body) == 1 and 
            isinstance(first_stmt.body[0], cst.Expr) and 
            isinstance(first_stmt.body[0].value, cst.SimpleString)):
            # This is a docstring, remove blank lines after it
            i = 1
            while i < len(body_list) and _is_blank_line(body_list[i]):
                body_list.pop(i)
                changed = True
            
            # Also check if the next statement has blank leading_lines
            if i < len(body_list) and isinstance(body_list[i], cst.SimpleStatementLine):
                next_stmt = body_list[i]
                if next_stmt.leading_lines:
                    new_leading = [line for line in next_stmt.leading_lines if not (isinstance(line, cst.EmptyLine) and line.comment is None)]
                    if len(new_leading) != len(next_stmt.leading_lines):
                        body_list[i] = next_stmt.with_changes(leading_lines=new_leading)
                        changed = True
    
    if not changed:
        return suite
    
    return suite.with_changes(body=body_list)


def fix_function_blank_lines(module: cst.Module) -> cst.Module:
    """Remove blank lines after function/method signatures throughout the module.
    
    This applies to:
    - Module-level functions
    - Class methods
    - Nested functions
    """
    
    class BlankLinesFixer(cst.CSTTransformer):
        def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
            # Fix blank lines in the function body
            new_body = _remove_leading_blank_lines_from_suite(updated_node.body)
            if new_body is not updated_node.body:
                return updated_node.with_changes(body=new_body)
            return updated_node
    
    transformer = BlankLinesFixer()
    modified_module = module.visit(transformer)
    return modified_module
