from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict

import libcst as cst

from .python_parser_import_index import PythonParserImportIndex


class PythonImportRewriter(cst.CSTTransformer):
    """Rewrite module-level imports by:
    - Removing symbols that will be localized to functions (A) or moved under TYPE_CHECKING (C-only)
    - Keeping symbols used at class-level property annotations (B)
    - Adding a TYPE_CHECKING block with required imports for C-only symbols
    - Ensuring `from typing import TYPE_CHECKING` is present
    """

    def __init__(
        self,
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
        self.found_type_checking_import: bool = False
        self.need_type_checking_block: bool = len(used_in_C_only) > 0

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

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.RemovalSentinel | cst.BaseSmallStatement:
        if updated_node.names is None or isinstance(updated_node.names, cst.ImportStar):
            return updated_node

        kept_aliases: list[cst.ImportAlias] = []
        for alias in updated_node.names:
            if not isinstance(alias, cst.ImportAlias):
                continue
            name = alias.name.value if isinstance(alias.name, cst.Name) else None
            if not name:
                continue
            alias_ident = alias.asname.name.value if alias.asname else name

            # Keep B at module level
            if alias_ident in self.used_in_B:
                kept_aliases.append(alias)
                continue

            # Drop if moved to TYPE_CHECKING or localized (A or C-only)
            if alias_ident in self.names_to_remove_from_module:
                continue

            kept_aliases.append(alias)

        if not kept_aliases:
            return cst.RemoveFromParent()
        return updated_node.with_changes(names=tuple(kept_aliases))

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        if not self.need_type_checking_block or not self.used_in_C_only:
            return updated_node

        # Build TYPE_CHECKING block
        type_checking_body: list[cst.BaseStatement] = []
        by_module: DefaultDict[str | None, list[str]] = defaultdict(list)
        for ident in sorted(self.used_in_C_only):
            mod, _ = self.idx.name_to_from.get(ident, (None, None))
            by_module[mod].append(ident)

        for mod, names in by_module.items():
            if not names:
                continue
            import_names = [cst.ImportAlias(name=cst.Name(n)) for n in sorted(names)]
            imp = cst.ImportFrom(
                module=cst.Name(mod) if mod else None, names=tuple(import_names)
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

        new_body: list[cst.CSTNode] = []
        inserted_typing_import = False

        i = 0
        while i < len(updated_node.body):
            stmt = updated_node.body[i]
            new_body.append(stmt)
            i += 1
            if not inserted_typing_import:
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
                        continue
                if not self.found_type_checking_import:
                    new_body.append(typing_import_stmt)
                inserted_typing_import = True

        type_checking_if = cst.If(
            test=cst.Name("TYPE_CHECKING"),
            body=cst.IndentedBlock(body=type_checking_body),
        )
        new_body.insert(1 if inserted_typing_import else 0, type_checking_if)

        return updated_node.with_changes(body=new_body)
