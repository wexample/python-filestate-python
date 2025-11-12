from __future__ import annotations

import libcst as cst


def fix_function_blank_lines(module: cst.Module) -> cst.Module:
    """Remove blank lines after function/method signatures and class definitions throughout the module.

    This applies to:
    - Module-level functions
    - Class methods
    - Nested functions
    - Class definitions (no blank lines after class signature)
    """

    class BlankLinesFixer(cst.CSTTransformer):
        def leave_FunctionDef(
            self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
        ) -> cst.FunctionDef:
            # Fix blank lines in the function body
            new_body = _remove_leading_blank_lines_from_suite(updated_node.body)
            if new_body is not updated_node.body:
                return updated_node.with_changes(body=new_body)
            return updated_node

        def leave_ClassDef(
            self, original_node: cst.ClassDef, updated_node: cst.ClassDef
        ) -> cst.ClassDef:
            # Fix blank lines in the class body
            new_body = _remove_leading_blank_lines_from_class_suite(
                updated_node.body, class_node=updated_node
            )
            if new_body is not updated_node.body:
                return updated_node.with_changes(body=new_body)
            return updated_node

    transformer = BlankLinesFixer()
    modified_module = module.visit(transformer)

    # Also fix module-level docstring spacing
    modified_module = _fix_module_docstring_spacing(modified_module)

    # Note: Module-level blank line normalization (between classes/functions/imports)
    # is handled by Black, so we don't duplicate that logic here.
    return modified_module


def _contains_union_operator(node: cst.CSTNode) -> bool:
    """Recursively check if a node contains the union operator (|)."""
    if isinstance(node, cst.BinaryOperation):
        if isinstance(node.operator, cst.BitOr):  # | operator
            return True
        return _contains_union_operator(node.left) or _contains_union_operator(
            node.right
        )
    return False


def _fix_module_docstring_spacing(module: cst.Module) -> cst.Module:
    """Fix spacing around module docstring: 0 lines before, 1 line after."""
    body_list = list(module.body)
    if not body_list:
        return module

    changed = False

    # Check if module has header with blank lines
    if module.header:
        # Remove blank lines from module header
        new_header = [
            line
            for line in module.header
            if not (isinstance(line, cst.EmptyLine) and line.comment is None)
        ]
        if len(new_header) != len(module.header):
            module = module.with_changes(header=new_header)
            changed = True

    # First, remove any leading EmptyLine elements at the start of the module
    while (
        body_list
        and isinstance(body_list[0], cst.EmptyLine)
        and body_list[0].comment is None
    ):
        body_list.pop(0)
        changed = True

    # Find module docstring (first statement that's a string literal)
    docstring_idx = -1
    for i, stmt in enumerate(body_list):
        if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1:
            small = stmt.body[0]
            if isinstance(small, cst.Expr) and isinstance(
                small.value, cst.SimpleString
            ):
                docstring_idx = i
                break
        # Stop at first non-simple statement
        elif not isinstance(stmt, cst.SimpleStatementLine):
            break

    if docstring_idx == -1:
        # No docstring found - ensure first statement has no leading blank lines
        if body_list:
            first_stmt = body_list[0]
            if hasattr(first_stmt, "leading_lines") and first_stmt.leading_lines:
                new_leading = [
                    line
                    for line in first_stmt.leading_lines
                    if not (isinstance(line, cst.EmptyLine) and line.comment is None)
                ]
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
            new_leading = [
                line
                for line in docstring_stmt.leading_lines
                if not (isinstance(line, cst.EmptyLine) and line.comment is None)
            ]
            if len(new_leading) != len(docstring_stmt.leading_lines):
                body_list[docstring_idx] = docstring_stmt.with_changes(
                    leading_lines=new_leading
                )
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
                non_blank_leading = [
                    line
                    for line in next_stmt.leading_lines
                    if not (isinstance(line, cst.EmptyLine) and line.comment is None)
                ]
                new_leading = [cst.EmptyLine()] + non_blank_leading
                body_list[next_idx] = next_stmt.with_changes(leading_lines=new_leading)
                changed = True

    if not changed:
        return module

    return module.with_changes(body=body_list)


def _has_default_value(node: cst.CSTNode) -> bool:
    """Check if a property assignment has a default value."""
    if isinstance(node, cst.SimpleStatementLine):
        if len(node.body) == 1:
            stmt = node.body[0]
            # Check for annotated assignment with default (e.g., x: int = 5)
            if isinstance(stmt, cst.AnnAssign):
                return stmt.value is not None
            # Check for regular assignment (e.g., x = 5)
            elif isinstance(stmt, cst.Assign):
                return True
    return False


def _is_blank_line(node: cst.CSTNode) -> bool:
    """Return True if node is an EmptyLine without a comment (blank line)."""
    return isinstance(node, cst.EmptyLine) and node.comment is None


def _is_class_definition(node: cst.CSTNode) -> bool:
    """Check if node is a class definition."""
    return isinstance(node, cst.ClassDef)


def _is_class_property(node: cst.CSTNode) -> bool:
    """Check if node is a class property (assignment statement)."""
    if isinstance(node, cst.SimpleStatementLine):
        if len(node.body) == 1 and isinstance(node.body[0], cst.Assign):
            # Check if it's a simple assignment (not a method or function)
            assign = node.body[0]
            if len(assign.targets) == 1:
                target = assign.targets[0].target
                return isinstance(target, cst.Name)
    return False


def _is_dataclass(class_node: cst.ClassDef) -> bool:
    """Check if a class has @dataclass decorator."""
    for decorator in class_node.decorators:
        if isinstance(decorator.decorator, cst.Name):
            if decorator.decorator.value == "dataclass":
                return True
        elif isinstance(decorator.decorator, cst.Call):
            if isinstance(decorator.decorator.func, cst.Name):
                if decorator.decorator.func.value == "dataclass":
                    return True
    return False


def _is_function_definition(node: cst.CSTNode) -> bool:
    """Check if node is a function definition."""
    return isinstance(node, cst.FunctionDef)


def _is_import_statement(node: cst.CSTNode) -> bool:
    """Check if node is an import statement."""
    return isinstance(node, (cst.Import, cst.ImportFrom))


def _is_lowercase_property(node: cst.CSTNode) -> bool:
    """Check if node is a lowercase class property."""
    if _is_class_property(node):
        assign = node.body[0]
        target = assign.targets[0].target
        if isinstance(target, cst.Name):
            return target.value.islower()
    return False


def _is_main_guard(node: cst.CSTNode) -> bool:
    """Check if node is an if __name__ == '__main__' block (Black compatibility)."""
    if isinstance(node, cst.If):
        test = node.test
        # Check for __name__ == "__main__" pattern
        if isinstance(test, cst.Comparison):
            if (
                len(test.comparisons) == 1
                and isinstance(test.left, cst.Name)
                and test.left.value == "__name__"
            ):
                comparison = test.comparisons[0]
                if (
                    isinstance(comparison.operator, cst.Equal)
                    and isinstance(comparison.comparator, cst.SimpleString)
                    and comparison.comparator.value in ('"__main__"', "'__main__'")
                ):
                    return True
    return False


def _is_type_alias(node: cst.CSTNode) -> bool:
    """Check if node is a type alias assignment (Black compatibility)."""
    if isinstance(node, cst.SimpleStatementLine):
        if len(node.body) == 1 and isinstance(node.body[0], cst.Assign):
            assign = node.body[0]
            if len(assign.targets) == 1:
                target = assign.targets[0].target
                # Type alias: variable name starts with uppercase or contains union (|)
                if isinstance(target, cst.Name):
                    name = target.value
                    # Check if it's a type alias pattern (starts with uppercase)
                    if name[0].isupper():
                        return True
                    # Check if assignment contains union operator (|) indicating type alias
                    if isinstance(assign.value, cst.BinaryOperation):
                        return _contains_union_operator(assign.value)
    return False


def _is_uppercase_property(node: cst.CSTNode) -> bool:
    """Check if node is an UPPERCASE class property."""
    if _is_class_property(node):
        assign = node.body[0]
        target = assign.targets[0].target
        if isinstance(target, cst.Name):
            return target.value.isupper()
    return False


def _normalize_class_properties_spacing(
    suite: cst.Suite, is_dataclass: bool = False
) -> cst.Suite:
    """Normalize spacing in class properties section.

    Rules:
    - No blank lines between properties
    - Exception: blank line when transitioning from UPPERCASE to lowercase properties
    - Exception (dataclass): blank line between required properties (no default) and optional properties (with default)
    - Blank line before first method after properties section
    """
    body_list = list(suite.body)
    if len(body_list) <= 1:
        return suite

    changed = False

    # Find the properties section (before first method)
    first_method_idx = -1
    for i, node in enumerate(body_list):
        if isinstance(node, cst.FunctionDef):
            first_method_idx = i
            break

    if first_method_idx == -1:
        # No methods found, apply to entire body
        first_method_idx = len(body_list)

    # Process properties section (skip if first element is docstring to avoid Black conflicts)
    start_idx = 1
    if (
        body_list
        and isinstance(body_list[0], cst.SimpleStatementLine)
        and len(body_list[0].body) == 1
        and isinstance(body_list[0].body[0], cst.Expr)
        and isinstance(body_list[0].body[0].value, cst.SimpleString)
    ):
        # First element is a docstring, start processing from index 2 to avoid modifying after docstring
        start_idx = 2

    for i in range(start_idx, first_method_idx):
        current_node = body_list[i]
        prev_node = body_list[i - 1]

        if not hasattr(current_node, "leading_lines"):
            continue

        # Count blank lines
        blank_count = sum(
            1
            for line in current_node.leading_lines
            if isinstance(line, cst.EmptyLine) and line.comment is None
        )

        # Determine if we should have a blank line
        should_have_blank = False

        # Check for UPPERCASE to lowercase transition
        if _is_uppercase_property(prev_node) and (
            _is_lowercase_property(current_node)
            or isinstance(current_node, cst.FunctionDef)
        ):
            should_have_blank = True

        # Check for dataclass: transition from no-default to with-default
        if is_dataclass:
            prev_has_default = _has_default_value(prev_node)
            current_has_default = _has_default_value(current_node)
            # Add blank line when transitioning from required to optional properties
            if not prev_has_default and current_has_default:
                should_have_blank = True

        # Normalize blank lines
        target_blanks = 1 if should_have_blank else 0

        if blank_count != target_blanks:
            non_blank_leading = [
                line
                for line in current_node.leading_lines
                if not (isinstance(line, cst.EmptyLine) and line.comment is None)
            ]
            new_leading = [cst.EmptyLine()] * target_blanks + non_blank_leading
            body_list[i] = current_node.with_changes(leading_lines=new_leading)
            changed = True

    # Ensure blank line before first method (if there are properties before it)
    if first_method_idx < len(body_list) and first_method_idx > 0:
        method_node = body_list[first_method_idx]
        prev_node = body_list[first_method_idx - 1]

        # Only add blank line if previous node is a property
        if _is_class_property(prev_node):
            if hasattr(method_node, "leading_lines"):
                blank_count = sum(
                    1
                    for line in method_node.leading_lines
                    if isinstance(line, cst.EmptyLine) and line.comment is None
                )

                if blank_count != 1:
                    non_blank_leading = [
                        line
                        for line in method_node.leading_lines
                        if not (
                            isinstance(line, cst.EmptyLine) and line.comment is None
                        )
                    ]
                    new_leading = [cst.EmptyLine()] + non_blank_leading
                    body_list[first_method_idx] = method_node.with_changes(
                        leading_lines=new_leading
                    )
                    changed = True

    if not changed:
        return suite

    return suite.with_changes(body=body_list)


def _normalize_double_blank_lines_in_suite(suite: cst.Suite) -> cst.Suite:
    """Normalize double blank lines inside function/method/class bodies to single blank lines."""
    body_list = list(suite.body)
    if len(body_list) <= 1:
        return suite

    changed = False

    for i in range(1, len(body_list)):
        current_node = body_list[i]

        if not hasattr(current_node, "leading_lines"):
            continue

        # Count blank lines in leading_lines
        blank_count = sum(
            1
            for line in current_node.leading_lines
            if isinstance(line, cst.EmptyLine) and line.comment is None
        )

        # Inside function/class bodies, allow maximum 1 blank line
        if blank_count > 1:
            # Keep non-blank leading lines and add exactly 1 blank line
            non_blank_leading = [
                line
                for line in current_node.leading_lines
                if not (isinstance(line, cst.EmptyLine) and line.comment is None)
            ]
            new_leading = [cst.EmptyLine()] + non_blank_leading
            body_list[i] = current_node.with_changes(leading_lines=new_leading)
            changed = True

    if not changed:
        return suite

    return suite.with_changes(body=body_list)


def _remove_leading_blank_lines_from_class_suite(
    suite: cst.Suite, class_node: cst.ClassDef | None = None
) -> cst.Suite:
    """Remove any leading blank lines from a class body suite.

    This ensures no blank lines appear immediately after the class signature.
    The first item (docstring, property, or method) should be directly under the class signature.
    If the first item is a docstring, the next item should be directly after the docstring.
    """
    body_list = list(suite.body)
    if not body_list:
        return suite

    changed = False
    is_dataclass = _is_dataclass(class_node) if class_node else False

    # Check first element for leading_lines with blank lines
    if body_list and isinstance(
        body_list[0], (cst.SimpleStatementLine, cst.FunctionDef, cst.ClassDef)
    ):
        first_stmt = body_list[0]
        if hasattr(first_stmt, "leading_lines") and first_stmt.leading_lines:
            # Remove blank leading lines from the first statement
            new_leading = [
                line
                for line in first_stmt.leading_lines
                if not (isinstance(line, cst.EmptyLine) and line.comment is None)
            ]
            if len(new_leading) != len(first_stmt.leading_lines):
                body_list[0] = first_stmt.with_changes(leading_lines=new_leading)
                changed = True

    # Remove leading blank EmptyLine nodes (but only before non-docstring elements)
    # Skip removal if first element is a docstring to avoid conflict with Black
    if body_list and not (
        isinstance(body_list[0], cst.SimpleStatementLine)
        and len(body_list[0].body) == 1
        and isinstance(body_list[0].body[0], cst.Expr)
        and isinstance(body_list[0].body[0].value, cst.SimpleString)
    ):
        # First element is not a docstring, safe to remove blank lines
        while body_list and _is_blank_line(body_list[0]):
            body_list.pop(0)
            changed = True

    # Allow Black's formatting for class docstrings - no blank line modifications
    # Normalize class properties spacing
    temp_suite = suite.with_changes(body=body_list) if changed else suite
    properties_normalized = _normalize_class_properties_spacing(
        temp_suite, is_dataclass=is_dataclass
    )

    # Normalize double blank lines in the rest of the class body
    normalized_suite = _normalize_double_blank_lines_in_suite(properties_normalized)

    return normalized_suite


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
            new_leading = [
                line
                for line in first_stmt.leading_lines
                if not (isinstance(line, cst.EmptyLine) and line.comment is None)
            ]
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
        if (
            len(first_stmt.body) == 1
            and isinstance(first_stmt.body[0], cst.Expr)
            and isinstance(first_stmt.body[0].value, cst.SimpleString)
        ):
            # This is a docstring, remove blank lines after it
            i = 1
            while i < len(body_list) and _is_blank_line(body_list[i]):
                body_list.pop(i)
                changed = True

            # Also check if the next statement has blank leading_lines
            if i < len(body_list) and isinstance(body_list[i], cst.SimpleStatementLine):
                next_stmt = body_list[i]
                if next_stmt.leading_lines:
                    new_leading = [
                        line
                        for line in next_stmt.leading_lines
                        if not (
                            isinstance(line, cst.EmptyLine) and line.comment is None
                        )
                    ]
                    if len(new_leading) != len(next_stmt.leading_lines):
                        body_list[i] = next_stmt.with_changes(leading_lines=new_leading)
                        changed = True

    # Normalize double blank lines in the function body
    temp_suite = suite.with_changes(body=body_list) if changed else suite
    normalized_suite = _normalize_double_blank_lines_in_suite(temp_suite)

    return normalized_suite
