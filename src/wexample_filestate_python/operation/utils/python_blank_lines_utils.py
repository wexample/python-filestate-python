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


def _fix_module_docstring_spacing(module: cst.Module) -> cst.Module:
    """Fix spacing around module docstring: 0 lines before, 1 line after."""
    body_list = list(module.body)
    if not body_list:
        return module
    
    changed = False
    
    # Check if module has header with blank lines
    if module.header:
        # Remove blank lines from module header
        new_header = [line for line in module.header if not (isinstance(line, cst.EmptyLine) and line.comment is None)]
        if len(new_header) != len(module.header):
            module = module.with_changes(header=new_header)
            changed = True
    
    # First, remove any leading EmptyLine elements at the start of the module
    while body_list and isinstance(body_list[0], cst.EmptyLine) and body_list[0].comment is None:
        body_list.pop(0)
        changed = True
    
    # Find module docstring (first statement that's a string literal)
    docstring_idx = -1
    for i, stmt in enumerate(body_list):
        if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1:
            small = stmt.body[0]
            if isinstance(small, cst.Expr) and isinstance(small.value, cst.SimpleString):
                docstring_idx = i
                break
        # Stop at first non-simple statement
        elif not isinstance(stmt, cst.SimpleStatementLine):
            break
    
    if docstring_idx == -1:
        # No docstring found - ensure first statement has no leading blank lines
        if body_list:
            first_stmt = body_list[0]
            if hasattr(first_stmt, 'leading_lines') and first_stmt.leading_lines:
                new_leading = [line for line in first_stmt.leading_lines if not (isinstance(line, cst.EmptyLine) and line.comment is None)]
                if len(new_leading) != len(first_stmt.leading_lines):
                    body_list[0] = first_stmt.with_changes(leading_lines=new_leading)
                    changed = True
        
        if not changed:
            return module
        return module.with_changes(body=body_list)
    
    docstring_stmt = body_list[docstring_idx]
    
    # Rule 1: 0 blank lines before module docstring
    if docstring_idx == 0:
        # Docstring is first - remove any leading blank lines
        if docstring_stmt.leading_lines:
            new_leading = [line for line in docstring_stmt.leading_lines if not (isinstance(line, cst.EmptyLine) and line.comment is None)]
            if len(new_leading) != len(docstring_stmt.leading_lines):
                body_list[docstring_idx] = docstring_stmt.with_changes(leading_lines=new_leading)
                changed = True
    
    # Rule 2: 1 blank line after module docstring
    next_idx = docstring_idx + 1
    if next_idx < len(body_list):
        next_stmt = body_list[next_idx]
        
        # Count existing blank lines after docstring
        blank_count = 0
        if isinstance(next_stmt, cst.SimpleStatementLine):
            # Count blank leading_lines
            for line in next_stmt.leading_lines:
                if isinstance(line, cst.EmptyLine) and line.comment is None:
                    blank_count += 1
        
        # Ensure exactly 1 blank line
        if blank_count != 1:
            if isinstance(next_stmt, cst.SimpleStatementLine):
                # Remove all blank leading lines and add exactly one
                non_blank_leading = [line for line in next_stmt.leading_lines if not (isinstance(line, cst.EmptyLine) and line.comment is None)]
                new_leading = [cst.EmptyLine()] + non_blank_leading
                body_list[next_idx] = next_stmt.with_changes(leading_lines=new_leading)
                changed = True
    
    if not changed:
        return module
    
    return module.with_changes(body=body_list)


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
    
    # Also fix module-level docstring spacing
    modified_module = _fix_module_docstring_spacing(modified_module)
    
    return modified_module
