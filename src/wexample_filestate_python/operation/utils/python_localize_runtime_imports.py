from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict

import libcst as cst

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

    @staticmethod
    def _build_module_expr(mod: str | None) -> cst.BaseExpression | None:
        if not mod:
            return None
        parts = mod.split(".")
        expr: cst.BaseExpression = cst.Name(parts[0])
        for p in parts[1:]:
            expr = cst.Attribute(value=expr, attr=cst.Name(p))
        return expr

    @staticmethod
    def _flatten_module_expr_to_str(module: cst.BaseExpression | None) -> str | None:
        if module is None:
            return None
        if isinstance(module, cst.Name):
            return module.value
        if isinstance(module, cst.Attribute):
            parts: list[str] = []
            cur: cst.BaseExpression | None = module
            while isinstance(cur, cst.Attribute):
                if isinstance(cur.attr, cst.Name):
                    parts.append(cur.attr.value)
                else:
                    break
                cur = cur.value
            if isinstance(cur, cst.Name):
                parts.append(cur.value)
            parts.reverse()
            return ".".join(parts) if parts else None
        return None

    def _build_local_imports(self, func_qname: str, existing_imported: set[tuple[str | None, str]]) -> list[cst.BaseStatement]:
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
            filtered = [n for n in sorted(idents) if (mod, n) not in existing_imported]
            if not filtered:
                continue
            import_names = [cst.ImportAlias(name=cst.Name(n)) for n in filtered]
            stmts.append(
                cst.SimpleStatementLine(
                    (
                        cst.ImportFrom(
                            module=self._build_module_expr(mod),
                            names=tuple(import_names),
                        ),
                    )
                )
            )
        return stmts

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # type: ignore[override]
        self.class_stack.append(node.name.value)
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:  # type: ignore[override]
        self.class_stack.pop()
        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        func_qname = (
            ".".join(self.class_stack + [original_node.name.value])
            if self.class_stack
            else original_node.name.value
        )
        # Scan existing from-imports in function body to avoid duplicates
        existing: set[tuple[str | None, str]] = set()
        for s in updated_node.body.body:
            if isinstance(s, cst.SimpleStatementLine) and len(s.body) == 1 and isinstance(s.body[0], cst.ImportFrom):
                imp: cst.ImportFrom = s.body[0]
                mod = self._flatten_module_expr_to_str(imp.module)
                if imp.names and not isinstance(imp.names, cst.ImportStar):
                    for alias in imp.names:
                        if isinstance(alias, cst.ImportAlias) and isinstance(alias.name, cst.Name):
                            existing.add((mod, alias.name.value))

        to_inject = self._build_local_imports(func_qname, existing)
        if not to_inject:
            return updated_node
        # Insert imports at the very top of the function body, after possible docstring
        body = list(updated_node.body.body)
        insert_at = (
            1
            if body
            and isinstance(body[0], cst.SimpleStatementLine)
            and any(
                isinstance(el, cst.Expr) and isinstance(el.value, cst.SimpleString)
                for el in body[0].body
            )
            else 0
        )
        new_body = body[:insert_at] + to_inject + body[insert_at:]
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )

    def leave_AsyncFunctionDef(
        self, original_node: cst.AsyncFunctionDef, updated_node: cst.AsyncFunctionDef
    ) -> cst.AsyncFunctionDef:
        func_qname = (
            ".".join(self.class_stack + [original_node.name.value])
            if self.class_stack
            else original_node.name.value
        )
        existing: set[tuple[str | None, str]] = set()
        for s in updated_node.body.body:
            if isinstance(s, cst.SimpleStatementLine) and len(s.body) == 1 and isinstance(s.body[0], cst.ImportFrom):
                imp: cst.ImportFrom = s.body[0]
                mod = self._flatten_module_expr_to_str(imp.module)
                if imp.names and not isinstance(imp.names, cst.ImportStar):
                    for alias in imp.names:
                        if isinstance(alias, cst.ImportAlias) and isinstance(alias.name, cst.Name):
                            existing.add((mod, alias.name.value))

        to_inject = self._build_local_imports(func_qname, existing)
        if not to_inject:
            return updated_node
        body = list(updated_node.body.body)
        insert_at = (
            1
            if body
            and isinstance(body[0], cst.SimpleStatementLine)
            and any(
                isinstance(el, cst.Expr) and isinstance(el.value, cst.SimpleString)
                for el in body[0].body
            )
            else 0
        )
        new_body = body[:insert_at] + to_inject + body[insert_at:]
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )
