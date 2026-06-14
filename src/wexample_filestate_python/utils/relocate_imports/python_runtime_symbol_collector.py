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
        self._annotation_depth: int = 0
        self.runtime_used_anywhere: set[str] = set()

    def leave_Annotation(self, node: cst.Annotation) -> None:  # type: ignore[override]
        self._annotation_depth -= 1

    # Track entering/leaving annotations
    def visit_Annotation(self, node: cst.Annotation) -> bool:  # type: ignore[override]
        self._annotation_depth += 1
        return True

    def visit_Attribute(self, node: cst.Attribute) -> bool:  # type: ignore[override]
        """Visit Attribute nodes to detect runtime usage of imported names.

        For example, in TerminalColor.RED, we need to mark TerminalColor as runtime-used.
        """
        if self._annotation_depth:
            return True
        # Walk the value (left side) to find the base name
        self._walk_for_runtime_names(node.value)
        return False  # Don't visit children since we handled it manually

    def visit_Name(self, node: cst.Name) -> None:  # type: ignore[override]
        if self._annotation_depth:
            return
        val = node.value
        if val in self.imported_value_names:
            self.runtime_used_anywhere.add(val)

    def _walk_for_runtime_names(self, expr: cst.BaseExpression) -> None:
        """Iteratively walk an expression to find imported names used at runtime."""
        imported = self.imported_value_names
        runtime = self.runtime_used_anywhere
        while True:
            if isinstance(expr, cst.Name):
                if expr.value in imported:
                    runtime.add(expr.value)
                return
            if isinstance(expr, (cst.Attribute, cst.Subscript)):
                expr = expr.value
            else:
                return
