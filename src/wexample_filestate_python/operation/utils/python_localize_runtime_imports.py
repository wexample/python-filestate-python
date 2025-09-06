from __future__ import annotations

from typing import DefaultDict

import libcst as cst
from collections import defaultdict

from .python_parser_import_index import PythonParserImportIndex


class PythonLocalizeRuntimeImports(cst.CSTTransformer):
    """Inject local imports into functions for runtime-only names (category A).

    For each function qualified name present in `functions_needing_local`, this transformer
    inserts grouped `from <module> import Name` statements at the top of the function body,
    after a docstring if present.
    """

    def __init__(
        self,
        idx: PythonParserImportIndex,
        functions_needing_local: DefaultDict[str, set[str]],
    ) -> None:
        super().__init__()
        self.idx = idx
        self.functions_needing_local = functions_needing_local
        self.class_stack: list[str] = []

    def _build_local_imports(self, func_qname: str) -> list[cst.BaseStatement]:
        names = self.functions_needing_local.get(func_qname)
        if not names:
            return []
        # Group by module
        by_module: DefaultDict[str | None, list[str]] = defaultdict(list)
        for ident in sorted(names):
            mod, _ = self.idx.name_to_from.get(ident, (None, None))
            by_module[mod].append(ident)
        stmts: list[cst.BaseStatement] = []
        for mod, idents in by_module.items():
            if not idents:
                continue
            import_names = [cst.ImportAlias(name=cst.Name(n)) for n in sorted(idents)]
            stmts.append(
                cst.SimpleStatementLine(
                    (
                        cst.ImportFrom(
                            module=cst.Name(mod) if mod else None,
                            names=tuple(import_names),
                        ),
                    )
                )
            )
        return stmts

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # type: ignore[override]
        self.class_stack.append(node.name.value)
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # type: ignore[override]
        self.class_stack.pop()

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        func_qname = ".".join(self.class_stack + [original_node.name.value]) if self.class_stack else original_node.name.value
        to_inject = self._build_local_imports(func_qname)
        if not to_inject:
            return updated_node
        # Insert imports at the very top of the function body, after possible docstring
        body = list(updated_node.body.body)
        insert_at = 1 if body and isinstance(body[0], cst.SimpleStatementLine) and any(
            isinstance(el, cst.Expr) and isinstance(el.value, cst.SimpleString) for el in body[0].body
        ) else 0
        new_body = body[:insert_at] + to_inject + body[insert_at:]
        return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))

    def leave_AsyncFunctionDef(self, original_node: cst.AsyncFunctionDef, updated_node: cst.AsyncFunctionDef) -> cst.AsyncFunctionDef:
        func_qname = ".".join(self.class_stack + [original_node.name.value]) if self.class_stack else original_node.name.value
        to_inject = self._build_local_imports(func_qname)
        if not to_inject:
            return updated_node
        body = list(updated_node.body.body)
        insert_at = 1 if body and isinstance(body[0], cst.SimpleStatementLine) and any(
            isinstance(el, cst.Expr) and isinstance(el.value, cst.SimpleString) for el in body[0].body
        ) else 0
        new_body = body[:insert_at] + to_inject + body[insert_at:]
        return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))
