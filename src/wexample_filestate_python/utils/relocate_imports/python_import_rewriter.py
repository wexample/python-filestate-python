from __future__ import annotations

from typing import TYPE_CHECKING, DefaultDict

import libcst as cst

if TYPE_CHECKING:
    from python_parser_import_index import PythonParserImportIndex


class PythonImportRewriter(cst.CSTTransformer):
    """Rewrite module-level imports by:
    - Removing symbols that will be localized to functions (A) or moved under TYPE_CHECKING (C-only)
    - Keeping symbols used at class-level property annotations (B)
    - Adding a TYPE_CHECKING block with required imports for C-only symbols
    - Ensuring `from typing import TYPE_CHECKING` is present
    """

    def __init__(
        self,
        *,
        used_in_B: set[str],
        names_to_remove_from_module: set[str],
        used_in_C_only: set[str],
        idx: PythonParserImportIndex,
    ) -> None:
        super().__init__()
        self.used_in_B = used_in_B
        self.names_to_remove_from_module = names_to_remove_from_module
        self.used_in_C_only = used_in_C_only
        self.idx = idx
        self.found_type_checking_import = False
        # Track whether we are at module level; only prune at module level
        self._inside_class_func_stack: list[str] = []
        self.need_type_checking_block: bool = len(used_in_C_only) > 0
        self._inside_type_checking_stack: list[bool] = []

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

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.BaseStatement:  # type: ignore[override]
        self._inside_class_func_stack.pop()
        return updated_node

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.BaseStatement:  # type: ignore[override]
        self._inside_class_func_stack.pop()
        return updated_node

    def leave_If(self, original_node: cst.If, updated_node: cst.If) -> cst.If:  # type: ignore[override]
        self._inside_type_checking_stack.pop()
        return updated_node

    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.RemovalSentinel | cst.BaseSmallStatement:
        # Only handle module-level imports
        if self._inside_class_func_stack:
            return updated_node
        kept_aliases: list[cst.ImportAlias] = []
        removed_any = False
        for alias in updated_node.names:
            if not isinstance(alias, cst.ImportAlias):
                continue

            # Extract the base module name (e.g., "os" from "import os.path")
            if isinstance(alias.name, cst.Name):
                name = alias.name.value
            elif isinstance(alias.name, cst.Attribute):
                # For "import os.path", extract the base name "os"
                full_name = self._flatten_module_expr_to_str(alias.name)
                if full_name and "." in full_name:
                    name = full_name.split(".")[0]
                else:
                    name = full_name
            else:
                continue

            if not name:
                continue
            alias_ident = alias.asname.name.value if alias.asname else name

            # Keep B at module level
            if alias_ident in self.used_in_B:
                kept_aliases.append(alias)
                continue

            # Drop if moved to TYPE_CHECKING or localized (A or C-only)
            if alias_ident in self.names_to_remove_from_module:
                removed_any = True
                continue

            kept_aliases.append(alias)

        if not kept_aliases:
            return cst.RemoveFromParent()

        # If nothing changed (same number of aliases kept as original and none removed),
        # return the original node to preserve exact formatting (commas, parentheses, whitespace).
        try:
            original_alias_count = len(original_node.names) if not isinstance(original_node.names, cst.ImportStar) else 0  # type: ignore[arg-type]
        except Exception:
            original_alias_count = -1
        if original_alias_count == len(kept_aliases) and not removed_any:
            return original_node

        # Rebuild aliases freshly to drop any stale trailing comma tokens.
        rebuilt_aliases: list[cst.ImportAlias] = []
        for alias in kept_aliases:
            rebuilt_aliases.append(
                cst.ImportAlias(
                    name=alias.name,
                    asname=alias.asname,
                )
            )
        return updated_node.with_changes(names=tuple(rebuilt_aliases))

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.RemovalSentinel | cst.BaseSmallStatement:
        # Only handle module-level imports
        if self._inside_class_func_stack:
            return updated_node
        if updated_node.names is None or isinstance(updated_node.names, cst.ImportStar):
            return updated_node

        # If we're already inside a TYPE_CHECKING block, do not filter out C-only names here.
        if self._inside_type_checking_stack and self._inside_type_checking_stack[-1]:
            return updated_node

        mod_str = self._flatten_module_expr_to_str(updated_node.module)

        kept_aliases: list[cst.ImportAlias] = []
        removed_any = False
        for alias in updated_node.names:
            if not isinstance(alias, cst.ImportAlias):
                continue
            name = alias.name.value if isinstance(alias.name, cst.Name) else None
            if not name:
                continue
            alias_ident = alias.asname.name.value if alias.asname else name

            # Always keep non-TYPE_CHECKING imports from typing at module level
            if mod_str == "typing" and name != "TYPE_CHECKING":
                kept_aliases.append(alias)
                continue

            # Keep B at module level
            if alias_ident in self.used_in_B:
                kept_aliases.append(alias)
                continue

            # Drop if moved to TYPE_CHECKING or localized (A or C-only)
            if alias_ident in self.names_to_remove_from_module:
                removed_any = True
                continue

            kept_aliases.append(alias)

        if not kept_aliases:
            return cst.RemoveFromParent()

        # If nothing changed (same number of aliases kept as original and none removed),
        # return the original node to preserve exact formatting (commas, parentheses, whitespace).
        try:
            original_alias_count = len(original_node.names) if not isinstance(original_node.names, cst.ImportStar) else 0  # type: ignore[arg-type]
        except Exception:
            original_alias_count = -1
        if original_alias_count == len(kept_aliases) and not removed_any:
            return original_node

        # Rebuild aliases freshly to drop any stale trailing comma tokens.
        rebuilt_aliases: list[cst.ImportAlias] = []
        for alias in kept_aliases:
            rebuilt_aliases.append(
                cst.ImportAlias(
                    name=alias.name,
                    asname=alias.asname,
                )
            )
        return updated_node.with_changes(names=tuple(rebuilt_aliases))

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        from collections import defaultdict

        if not self.need_type_checking_block or not self.used_in_C_only:
            return updated_node

        # Build desired imports for C-only
        desired_by_module: DefaultDict[str | None, set[str]] = defaultdict(set)
        for ident in sorted(self.used_in_C_only):
            mod, _ = self.idx.name_to_from.get(ident, (None, None))
            # Never add typing.* under TYPE_CHECKING; keep them at module level only.
            if mod == "typing":
                continue
            desired_by_module[mod].add(ident)

        # Look for existing TYPE_CHECKING block(s)
        existing_tc_index = None
        existing_tc_body: list[cst.BaseStatement] | None = None
        existing_imported: set[tuple[str | None, str]] = set()

        for i, stmt in enumerate(updated_node.body):
            if (
                isinstance(stmt, cst.If)
                and isinstance(stmt.test, cst.Name)
                and stmt.test.value == "TYPE_CHECKING"
            ):
                existing_tc_index = i
                existing_tc_body = list(stmt.body.body)
                # Collect names already imported there
                for s in existing_tc_body:
                    if (
                        isinstance(s, cst.SimpleStatementLine)
                        and len(s.body) == 1
                        and isinstance(s.body[0], cst.ImportFrom)
                    ):
                        imp: cst.ImportFrom = s.body[0]
                        mod = self._flatten_module_expr_to_str(imp.module)
                        if imp.names and not isinstance(imp.names, cst.ImportStar):
                            for alias in imp.names:
                                if isinstance(alias, cst.ImportAlias) and isinstance(
                                    alias.name, cst.Name
                                ):
                                    existing_imported.add((mod, alias.name.value))
                break

        # Compute missing imports
        missing_by_module: DefaultDict[str | None, list[str]] = defaultdict(list)
        for mod, names in desired_by_module.items():
            for n in sorted(names):
                if (mod, n) not in existing_imported:
                    missing_by_module[mod].append(n)

        if existing_tc_index is not None and existing_tc_body is not None:
            # Append missing imports to existing TYPE_CHECKING block
            additions: list[cst.BaseStatement] = []
            for mod, names in missing_by_module.items():
                if not names:
                    continue
                import_names = [
                    cst.ImportAlias(name=cst.Name(n)) for n in sorted(names)
                ]
                imp_stmt = cst.SimpleStatementLine(
                    (
                        cst.ImportFrom(
                            module=self._build_module_expr(mod),
                            names=tuple(import_names),
                        ),
                    )
                )
                additions.append(imp_stmt)
            if not additions:
                return original_node
            new_tc = updated_node.body[existing_tc_index].with_changes(
                body=cst.IndentedBlock(body=existing_tc_body + additions)
            )
            new_body = list(updated_node.body)
            new_body[existing_tc_index] = new_tc
            return updated_node.with_changes(body=new_body)

        # Otherwise, create a new TYPE_CHECKING block placed after imports
        type_checking_body: list[cst.BaseStatement] = []
        for mod, names in missing_by_module.items():
            if not names:
                continue
            import_names = [cst.ImportAlias(name=cst.Name(n)) for n in sorted(names)]
            imp = cst.ImportFrom(
                module=self._build_module_expr(mod), names=tuple(import_names)
            )
            type_checking_body.append(cst.SimpleStatementLine((imp,)))

        if not type_checking_body:
            return updated_node

        typing_import_stmt = cst.SimpleStatementLine(
            (
                cst.ImportFrom(
                    module=cst.Name("typing"),
                    names=(cst.ImportAlias(name=cst.Name("TYPE_CHECKING")),),
                ),
            )
        )

        # Find insertion index: after module docstring (if any) and after __future__ imports,
        # then after consecutive top-level imports. Never before the docstring or __future__.
        insert_index = 0
        i = 0
        # Skip module docstring at very top
        if i < len(updated_node.body):
            stmt0 = updated_node.body[i]
            if isinstance(stmt0, cst.SimpleStatementLine) and any(
                isinstance(el, cst.Expr) and isinstance(el.value, cst.SimpleString)
                for el in stmt0.body
            ):
                i += 1
                insert_index = i

        # Skip __future__ imports
        while i < len(updated_node.body):
            stmt = updated_node.body[i]
            if (
                isinstance(stmt, cst.SimpleStatementLine)
                and stmt.body
                and isinstance(stmt.body[0], cst.ImportFrom)
            ):
                imp: cst.ImportFrom = stmt.body[0]
                if (
                    imp.module
                    and isinstance(imp.module, cst.Name)
                    and imp.module.value == "__future__"
                ):
                    i += 1
                    insert_index = i
                    continue
            break
        # Walk through consecutive import statements
        while i < len(updated_node.body):
            stmt = updated_node.body[i]
            if (
                isinstance(stmt, cst.SimpleStatementLine)
                and stmt.body
                and (
                    isinstance(stmt.body[0], cst.ImportFrom)
                    or isinstance(stmt.body[0], cst.Import)
                )
            ):
                i += 1
                insert_index = i
            else:
                break

        new_body = list(updated_node.body)
        # Ensure typing import exists somewhere before the TYPE_CHECKING block
        if not self.found_type_checking_import:
            new_body.insert(insert_index, typing_import_stmt)
            insert_index += 1

        type_checking_if = cst.If(
            test=cst.Name("TYPE_CHECKING"),
            body=cst.IndentedBlock(body=type_checking_body),
        )
        new_body.insert(insert_index, type_checking_if)

        return updated_node.with_changes(body=new_body)

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.BaseStatement:
        # Detect `from typing import TYPE_CHECKING`
        if len(updated_node.body) == 1 and isinstance(
            updated_node.body[0], cst.ImportFrom
        ):
            imp: cst.ImportFrom = updated_node.body[0]
            if (
                imp.module
                and isinstance(imp.module, cst.Name)
                and imp.module.value == "typing"
                and imp.names
                and not isinstance(imp.names, cst.ImportStar)
            ):
                for alias in imp.names:
                    if isinstance(alias, cst.ImportAlias) and isinstance(
                        alias.name, cst.Name
                    ):
                        if alias.name.value == "TYPE_CHECKING":
                            self.found_type_checking_import = True
        return updated_node

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # type: ignore[override]
        self._inside_class_func_stack.append("class")
        return True

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # type: ignore[override]
        self._inside_class_func_stack.append("function")
        return True

    def visit_If(self, node: cst.If) -> bool:  # type: ignore[override]
        # Track whether we are under `if TYPE_CHECKING:`
        inside = isinstance(node.test, cst.Name) and node.test.value == "TYPE_CHECKING"
        self._inside_type_checking_stack.append(inside)
        return True
