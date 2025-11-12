from __future__ import annotations

from typing import TYPE_CHECKING, DefaultDict

import libcst as cst

if TYPE_CHECKING:
    from python_parser_import_index import PythonParserImportIndex


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
        skip_local_names: set[str] | None = None,
    ) -> None:
        super().__init__()
        self.idx = idx
        self.functions_needing_local = functions_needing_local
        self.skip_local_names = skip_local_names or set()
        self.class_stack: list[str] = []
        self.func_stack: list[str] = []

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

    def leave_AsyncFunctionDef(
        self, original_node: cst.AsyncFunctionDef, updated_node: cst.AsyncFunctionDef
    ) -> cst.AsyncFunctionDef:
        func_qname = (
            ".".join(self.class_stack + self.func_stack + [original_node.name.value])
            if (self.class_stack or self.func_stack)
            else original_node.name.value
        )
        self.func_stack.pop()
        to_inject, pairs = self._build_local_imports(func_qname)
        if not to_inject:
            return updated_node

        # Collect existing imports
        def _collect_current_pairs(
            fn: cst.AsyncFunctionDef,
        ) -> set[tuple[str | None, str]]:
            found: set[tuple[str | None, str]] = set()

            class _Find(cst.CSTVisitor):
                def leave_ImportFrom(self, node: cst.ImportFrom) -> None:  # type: ignore[override]
                    if node.names is None or isinstance(node.names, cst.ImportStar):
                        return
                    mod = PythonLocalizeRuntimeImports._flatten_module_expr_to_str(
                        node.module
                    )
                    for alias in node.names:
                        if isinstance(alias, cst.ImportAlias) and isinstance(
                            alias.name, cst.Name
                        ):
                            found.add((mod, alias.name.value))

            fn.visit(_Find())
            return found

        existing = _collect_current_pairs(updated_node)
        if pairs.issubset(existing):
            return original_node

        # Filter out pairs that already exist (exact module + name match)
        # This avoids duplicate imports of the same symbol
        pairs_to_add = pairs - existing

        # If no new pairs to add after filtering, return original
        if not pairs_to_add:
            return original_node

        class _PruneInner(cst.CSTTransformer):
            def leave_ImportFrom(self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom):  # type: ignore[override]
                if updated_node.names is None or isinstance(
                    updated_node.names, cst.ImportStar
                ):
                    return updated_node
                mod = PythonLocalizeRuntimeImports._flatten_module_expr_to_str(
                    updated_node.module
                )
                kept_aliases: list[cst.ImportAlias] = []
                for alias in updated_node.names:
                    if not isinstance(alias, cst.ImportAlias):
                        continue
                    name = (
                        alias.name.value if isinstance(alias.name, cst.Name) else None
                    )
                    if not name:
                        continue
                    if (mod, name) in pairs_to_add:
                        continue
                    kept_aliases.append(alias)
                if not kept_aliases:
                    return cst.RemoveFromParent()
                return updated_node.with_changes(names=tuple(kept_aliases))

        pruned_node = updated_node.visit(_PruneInner())
        body = list(pruned_node.body.body)
        insert_at = 0
        if (
            body
            and isinstance(body[0], cst.SimpleStatementLine)
            and any(
                isinstance(el, cst.Expr) and isinstance(el.value, cst.SimpleString)
                for el in body[0].body
            )
        ):
            insert_at = 1

        # Build only the imports we need to add (filtered)
        to_inject_filtered = self._build_import_statements_from_pairs(pairs_to_add)
        new_body = body[:insert_at] + to_inject_filtered + body[insert_at:]
        return pruned_node.with_changes(
            body=pruned_node.body.with_changes(body=new_body)
        )

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:  # type: ignore[override]
        self.class_stack.pop()
        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        func_qname = (
            ".".join(self.class_stack + self.func_stack + [original_node.name.value])
            if (self.class_stack or self.func_stack)
            else original_node.name.value
        )
        self.func_stack.pop()
        # Build consolidated imports and list of pairs to hoist
        to_inject, pairs = self._build_local_imports(func_qname)
        if not to_inject:
            return updated_node

        # If all target imports are already present somewhere in the function body,
        # avoid rewriting to preserve existing order/formatting.
        def _collect_current_pairs(fn: cst.FunctionDef) -> set[tuple[str | None, str]]:
            found: set[tuple[str | None, str]] = set()

            class _Find(cst.CSTVisitor):
                def leave_ImportFrom(self, node: cst.ImportFrom) -> None:  # type: ignore[override]
                    if node.names is None or isinstance(node.names, cst.ImportStar):
                        return
                    mod = PythonLocalizeRuntimeImports._flatten_module_expr_to_str(
                        node.module
                    )
                    for alias in node.names:
                        if isinstance(alias, cst.ImportAlias) and isinstance(
                            alias.name, cst.Name
                        ):
                            found.add((mod, alias.name.value))

                def leave_Import(self, node: cst.Import) -> None:  # type: ignore[override]
                    return

            fn.visit(_Find())
            return found

        existing = _collect_current_pairs(updated_node)
        if pairs.issubset(existing):
            return original_node

        # Filter out pairs that already exist (exact module + name match)
        # This avoids duplicate imports of the same symbol
        pairs_to_add = pairs - existing

        # If no new pairs to add after filtering, return original
        if not pairs_to_add:
            return original_node

        # First prune matching imports anywhere within the function body
        class _PruneInner(cst.CSTTransformer):
            def leave_ImportFrom(self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom):  # type: ignore[override]
                if updated_node.names is None or isinstance(
                    updated_node.names, cst.ImportStar
                ):
                    return updated_node
                mod = PythonLocalizeRuntimeImports._flatten_module_expr_to_str(
                    updated_node.module
                )
                kept_aliases: list[cst.ImportAlias] = []
                for alias in updated_node.names:
                    if not isinstance(alias, cst.ImportAlias):
                        continue
                    name = (
                        alias.name.value if isinstance(alias.name, cst.Name) else None
                    )
                    if not name:
                        continue
                    if (mod, name) in pairs_to_add:
                        continue
                    kept_aliases.append(alias)
                if not kept_aliases:
                    return cst.RemoveFromParent()
                return updated_node.with_changes(names=tuple(kept_aliases))

        pruned_node = updated_node.visit(_PruneInner())
        body = list(pruned_node.body.body)
        insert_at = 0
        if (
            body
            and isinstance(body[0], cst.SimpleStatementLine)
            and any(
                isinstance(el, cst.Expr) and isinstance(el.value, cst.SimpleString)
                for el in body[0].body
            )
        ):
            insert_at = 1

        # Build only the imports we need to add (filtered)
        to_inject_filtered = self._build_import_statements_from_pairs(pairs_to_add)
        new_body = body[:insert_at] + to_inject_filtered + body[insert_at:]
        return pruned_node.with_changes(
            body=pruned_node.body.with_changes(body=new_body)
        )

    def visit_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> bool:  # type: ignore[override]
        self.func_stack.append(node.name.value)
        return True

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # type: ignore[override]
        self.class_stack.append(node.name.value)
        return True

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # type: ignore[override]
        self.func_stack.append(node.name.value)
        return True

    def _build_import_statements_from_pairs(
        self, pairs: set[tuple[str | None, str]]
    ) -> list[cst.BaseStatement]:
        """Build import statements from a set of (module, name) pairs."""
        from collections import defaultdict

        by_module: DefaultDict[str | None, list[str]] = defaultdict(list)
        for mod, name in pairs:
            by_module[mod].append(name)

        stmts: list[cst.BaseStatement] = []
        for mod, idents in by_module.items():
            if not idents:
                continue
            import_names = [cst.ImportAlias(name=cst.Name(n)) for n in sorted(idents)]
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

    def _build_local_imports(
        self, func_qname: str
    ) -> tuple[list[cst.BaseStatement], set[tuple[str | None, str]]]:
        from collections import defaultdict

        names = self.functions_needing_local.get(func_qname)
        if not names:
            return [], set()
        # Group by module
        by_module: DefaultDict[str | None, list[str]] = defaultdict(list)
        for ident in sorted(names):
            if ident in self.skip_local_names:
                continue
            mod, _ = self.idx.name_to_from.get(ident, (None, None))
            # Skip unresolved modules to avoid invalid ImportFrom(module=None)
            if mod is None:
                continue
            # Never inject local imports from typing; keep them at module level
            if mod == "typing":
                continue
            by_module[mod].append(ident)
        stmts: list[cst.BaseStatement] = []
        pairs: set[tuple[str | None, str]] = set()
        for mod, idents in by_module.items():
            if not idents:
                continue
            for n in sorted(idents):
                pairs.add((mod, n))
            import_names = [cst.ImportAlias(name=cst.Name(n)) for n in sorted(idents)]
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
        return stmts, pairs
