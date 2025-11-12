from __future__ import annotations

import libcst as cst


class PythonRuntimeSymbolCollector(cst.CSTVisitor):
    """Collect imported symbol names used in non-annotation runtime expressions.

    It ignores names that appear inside annotations and records names that appear
    elsewhere, so callers can conservatively treat them as runtime-used and keep
    their imports at module level (and/or avoid moving them under TYPE_CHECKING).
    """

    def __init__(self, imported_value_names: set[str]) -> None:
        super().__init__()
        self.imported_value_names = imported_value_names
        self.in_annotation_stack: list[bool] = []
        self.runtime_used_anywhere: set[str] = set()

    def leave_Annotation(self, node: cst.Annotation) -> None:  # type: ignore[override]
        self.in_annotation_stack.pop()

    # Track entering/leaving annotations
    def visit_Annotation(self, node: cst.Annotation) -> bool:  # type: ignore[override]
        self.in_annotation_stack.append(True)
        return True

    def visit_Attribute(self, node: cst.Attribute) -> bool:  # type: ignore[override]
        """Visit Attribute nodes to detect runtime usage of imported names.

        For example, in TerminalColor.RED, we need to mark TerminalColor as runtime-used.
        """
        if self.in_annotation_stack:
            return True
        # Walk the value (left side) to find the base name
        self._walk_for_runtime_names(node.value)
        return False  # Don't visit children since we handled it manually

    def visit_Name(self, node: cst.Name) -> None:  # type: ignore[override]
        if self.in_annotation_stack:
            return
        val = node.value
        if val in self.imported_value_names:
            self.runtime_used_anywhere.add(val)

    def _walk_for_runtime_names(self, expr: cst.BaseExpression) -> None:
        """Recursively walk an expression to find imported names used at runtime."""
        if isinstance(expr, cst.Name):
            if expr.value in self.imported_value_names:
                self.runtime_used_anywhere.add(expr.value)
        elif isinstance(expr, cst.Attribute):
            # Recurse into the value (left side) only
            self._walk_for_runtime_names(expr.value)
        elif isinstance(expr, cst.Subscript):
            self._walk_for_runtime_names(expr.value)
