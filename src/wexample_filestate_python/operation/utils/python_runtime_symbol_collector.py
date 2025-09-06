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

    # Track entering/leaving annotations
    def visit_Annotation(self, node: cst.Annotation) -> bool:  # type: ignore[override]
        self.in_annotation_stack.append(True)
        return True

    def leave_Annotation(self, node: cst.Annotation) -> None:  # type: ignore[override]
        self.in_annotation_stack.pop()

    def visit_Name(self, node: cst.Name) -> None:  # type: ignore[override]
        if self.in_annotation_stack:
            return
        val = node.value
        if val in self.imported_value_names:
            self.runtime_used_anywhere.add(val)
