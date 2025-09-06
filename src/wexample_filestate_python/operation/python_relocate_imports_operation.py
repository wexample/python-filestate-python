from __future__ import annotations

from typing import ClassVar, DefaultDict, Iterable

from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType

from .abstract_python_file_operation import AbstractPythonFileOperation


class PythonRelocateImportsOperation(AbstractPythonFileOperation):
    """Relocate imports according to usage categories A/B/C.

    Rules:
    - A (runtime inside a method): names instantiated or used as runtime-only within
      a function/method (e.g., return MyClass(), typing.cast(x, MyClass)).
      -> import locally at the top of each function using it.
    - B (class-level property types): names used in class attributes annotations
      (e.g., prop: MyClass, prop: MyClass = Field(...)).
      -> keep/import at module top level.
    - C (type-only annotations): names used exclusively in annotations (function
      params/returns, module-level annotations) and not in A or B.
      -> move under `if TYPE_CHECKING:` at module top (add "from typing import TYPE_CHECKING"
         if missing). No need to add `from __future__ import annotations` as files already have it.

    Triggered by config: { "python": ["relocate_imports"] }
    """

    # Names that we treat as a call to typing.cast in code detection.
    _cast_function_candidates: ClassVar[set[str]] = {"cast"}

    @classmethod
    def get_option_name(cls) -> str:
        # Return literal to avoid relying on an updated PythonConfigOption constant.
        return "relocate_imports"

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from libcst import matchers as m
        from collections import defaultdict

        src = cls._read_current_str_or_fail(target)

        try:
            module = cst.parse_module(src)
        except Exception:
            # Fallback: keep content unchanged if parse fails.
            return src

        # Collect existing from-imports into a map: imported_name -> (module, alias)
        # Only handle `from pkg import Name [as Alias]`. Skip star imports and bare `import pkg`.
        class ImportIndex(cst.CSTVisitor):
            def __init__(self) -> None:
                self.name_to_from: dict[str, tuple[str | None, str | None]] = {}
                self.importfrom_nodes: list[cst.ImportFrom] = []
                self.other_import_nodes: list[cst.Import] = []

            def visit_ImportFrom(self, node: cst.ImportFrom) -> None:  # type: ignore[override]
                self.importfrom_nodes.append(node)
                if node.names is None or isinstance(node.names, cst.ImportStar):
                    return
                module_name = None
                if node.module is not None:
                    if isinstance(node.module, cst.Name):
                        module_name = node.module.value
                    elif isinstance(node.module, cst.Attribute):
                        module_name = node.module.attr.value if isinstance(node.module.attr, cst.Name) else None
                    elif isinstance(node.module, cst.SimpleString):
                        module_name = node.module.evaluated_value  # unlikely
                for alias in node.names:
                    if isinstance(alias, cst.ImportAlias):
                        asname = alias.asname.name.value if alias.asname else None
                        name = alias.name.value if isinstance(alias.name, cst.Name) else None
                        if name:
                            self.name_to_from[name if not asname else asname] = (module_name, asname)

            def visit_Import(self, node: cst.Import) -> None:  # type: ignore[override]
                self.other_import_nodes.append(node)

        idx = ImportIndex()
        module.visit(idx)

        imported_value_names: set[str] = set(idx.name_to_from.keys())

        # Usage collection
        # A: runtime usage inside function bodies
        # B: property type usage inside class body annotations
        # C: type-only annotations across module if not in A or B
        functions_needing_local: DefaultDict[str, set[str]] = defaultdict(set)  # func_qualified_name -> names
        used_in_B: set[str] = set()
        used_in_C_annot: set[str] = set()

        # Helper: get a simple qualified function name for stable mapping
        def _qualified_func_name(stack: list[str], node: cst.BaseFunctionDef) -> str:
            base = node.name.value if isinstance(node, cst.FunctionDef) else getattr(node, "name", None)
            q = ".".join(stack + ([base] if base else []))
            return q or "<lambda>"

        class UsageCollector(cst.CSTVisitor):
            def __init__(self) -> None:
                self.class_stack: list[str] = []
                self.func_stack: list[str] = []

            # Track class/func stack
            def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # type: ignore[override]
                self.class_stack.append(node.name.value)
                return True

            def leave_ClassDef(self, node: cst.ClassDef) -> None:  # type: ignore[override]
                self.class_stack.pop()

            def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # type: ignore[override]
                self.func_stack.append(_qualified_func_name(self.class_stack, node))
                return True

            def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # type: ignore[override]
                self.func_stack.pop()

            def visit_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> bool:  # type: ignore[override]
                self.func_stack.append(_qualified_func_name(self.class_stack, node))
                return True

            def leave_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> None:  # type: ignore[override]
                self.func_stack.pop()

            # A: runtime inside functions
            def visit_Call(self, node: cst.Call) -> None:  # type: ignore[override]
                if not self.func_stack:
                    return
                # Case: return MyClass(...) or general call inside function
                func = node.func
                if isinstance(func, cst.Name):
                    callee = func.value
                    if callee in imported_value_names and callee[:1].isupper():
                        functions_needing_local[self.func_stack[-1]].add(callee)
                        return
                    # typing.cast(x, MyClass)
                    if callee in PythonRelocateImportsOperation._cast_function_candidates and node.args:
                        if len(node.args) >= 2:
                            second = node.args[1].value
                            if isinstance(second, cst.Name) and second.value in imported_value_names:
                                functions_needing_local[self.func_stack[-1]].add(second.value)
                                return
                elif isinstance(func, cst.Attribute):
                    # typing.cast(...) or pkg.cast(...)
                    if isinstance(func.attr, cst.Name) and func.attr.value in PythonRelocateImportsOperation._cast_function_candidates:
                        if node.args and len(node.args) >= 2:
                            second = node.args[1].value
                            if isinstance(second, cst.Name) and second.value in imported_value_names:
                                functions_needing_local[self.func_stack[-1]].add(second.value)
                                return

            # B: class-level property annotations
            def visit_AnnAssign(self, node: cst.AnnAssign) -> None:  # type: ignore[override]
                # Only count as B if inside class body
                if not self.class_stack:
                    # module-level AnnAssign -> C consideration
                    self._record_type_names(node.annotation.annotation, used_in_C_annot)
                    return
                self._record_type_names(node.annotation.annotation, used_in_B)

            # C: function annotations
            def visit_Param(self, node: cst.Param) -> None:  # type: ignore[override]
                if node.annotation is not None:
                    self._record_type_names(node.annotation.annotation, used_in_C_annot)

            def visit_FunctionDef_returns(self, node: cst.FunctionDef) -> None:
                pass

            def visit_ReturnAnnotation(self, node: cst.Annotation) -> None:
                # Not used directly by LibCST; we'll handle returns via FunctionDef
                pass

            def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # type: ignore[override]
                if node.returns is not None:
                    self._record_type_names(node.returns.annotation, used_in_C_annot)
                return True

            def visit_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> bool:  # type: ignore[override]
                if node.returns is not None:
                    self._record_type_names(node.returns.annotation, used_in_C_annot)
                return True

            # Utility to collect Name identifiers from type expressions conservatively
            def _record_type_names(self, ann: cst.BaseExpression, bucket: set[str]) -> None:
                # We only record simple Name or Attribute tail as Name for imported identifiers
                if isinstance(ann, cst.Name):
                    if ann.value in imported_value_names:
                        bucket.add(ann.value)
                elif isinstance(ann, cst.Subscript):
                    # e.g., Optional[MyClass], list[MyClass]
                    self._walk_expr_for_names(ann.value, bucket)
                    for e in ann.slice:
                        if isinstance(e, cst.SubscriptElement) and isinstance(e.slice, cst.Index):
                            self._walk_expr_for_names(e.slice.value, bucket)
                else:
                    self._walk_expr_for_names(ann, bucket)

            def _walk_expr_for_names(self, expr: cst.BaseExpression, bucket: set[str]) -> None:
                # Collect Names that directly match imported names
                if isinstance(expr, cst.Name):
                    if expr.value in imported_value_names:
                        bucket.add(expr.value)
                elif isinstance(expr, cst.Attribute):
                    if isinstance(expr.attr, cst.Name) and expr.attr.value in imported_value_names:
                        bucket.add(expr.attr.value)
                elif isinstance(expr, cst.Subscript):
                    self._walk_expr_for_names(expr.value, bucket)
                    for e in expr.slice:
                        if isinstance(e, cst.SubscriptElement) and isinstance(e.slice, cst.Index):
                            self._walk_expr_for_names(e.slice.value, bucket)

        uc = UsageCollector()
        module.visit(uc)

        # Resolve categories
        used_in_A_all_functions: set[str] = set().union(*functions_needing_local.values()) if functions_needing_local else set()
        # B has priority over A: if a name is in B, we will NOT local-import it (keep at module level)
        used_in_A_final: set[str] = {n for n in used_in_A_all_functions if n not in used_in_B}
        # C-only = in type annotations but not A_final or B
        used_in_C_only: set[str] = {n for n in used_in_C_annot if n not in used_in_A_final and n not in used_in_B}

        # Prepare transformations
        # 1) Adjust module-level ImportFrom nodes: remove names that move to A (local) or C-only (TYPE_CHECKING),
        #    except when also in B.
        names_to_remove_from_module: set[str] = set(used_in_A_final) | set(used_in_C_only)

        class ImportRewriter(cst.CSTTransformer):
            def __init__(self) -> None:
                super().__init__()
                self.found_type_checking_import: bool = False
                self.need_type_checking_block: bool = len(used_in_C_only) > 0

            def leave_SimpleStatementLine(
                    self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
            ) -> cst.BaseStatement:
                # Detect from typing import TYPE_CHECKING
                if len(updated_node.body) == 1 and isinstance(updated_node.body[0], cst.ImportFrom):
                    imp: cst.ImportFrom = updated_node.body[0]
                    if (
                            imp.module
                            and isinstance(imp.module, cst.Name)
                            and imp.module.value == "typing"
                            and imp.names
                            and not isinstance(imp.names, cst.ImportStar)
                    ):
                        for alias in imp.names:
                            if isinstance(alias, cst.ImportAlias) and isinstance(alias.name, cst.Name):
                                if alias.name.value == "TYPE_CHECKING":
                                    self.found_type_checking_import = True
                return updated_node

            def leave_ImportFrom(
                    self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
            ) -> cst.RemovalSentinel | cst.BaseSmallStatement:
                if updated_node.names is None or isinstance(updated_node.names, cst.ImportStar):
                    return updated_node

                # Build filtered aliases
                kept_aliases: list[cst.ImportAlias] = []
                moved_to_tc_aliases: list[cst.ImportAlias] = []
                for alias in updated_node.names:
                    if not isinstance(alias, cst.ImportAlias):
                        continue
                    name = alias.name.value if isinstance(alias.name, cst.Name) else None
                    if not name:
                        continue
                    alias_ident = alias.asname.name.value if alias.asname else name
                    # If this alias is used in B, keep it at module level
                    if alias_ident in used_in_B:
                        kept_aliases.append(alias)
                        continue
                    # If this alias should be moved away from module level
                    if alias_ident in names_to_remove_from_module:
                        # If it is C-only, we will later re-add it under TYPE_CHECKING
                        if alias_ident in used_in_C_only:
                            moved_to_tc_aliases.append(alias)
                        # If it is in A, it will be locally imported in functions; drop from module
                        # by not appending to kept_aliases
                        continue
                    # Otherwise keep
                    kept_aliases.append(alias)

                if not kept_aliases:
                    # If nothing left, remove the whole statement
                    return cst.RemoveFromParent()

                return updated_node.with_changes(names=tuple(kept_aliases))

            def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
                # Insert TYPE_CHECKING block (and import) if needed
                if not self.need_type_checking_block or not used_in_C_only:
                    return updated_node

                # Build the TYPE_CHECKING block with the necessary imports
                type_checking_body: list[cst.BaseStatement] = []

                # Reconstruct imports for C-only names from idx.name_to_from mapping
                # Group by module for nicer grouping
                by_module: DefaultDict[str | None, list[str]] = defaultdict(list)
                for ident in sorted(used_in_C_only):
                    mod, _ = idx.name_to_from.get(ident, (None, None))
                    by_module[mod].append(ident)

                for mod, names in by_module.items():
                    if not names:
                        continue
                    import_names = [
                        cst.ImportAlias(name=cst.Name(n)) for n in sorted(names)
                    ]
                    imp = cst.ImportFrom(
                        module=cst.Name(mod) if mod else None,
                        names=tuple(import_names),
                    )
                    type_checking_body.append(cst.SimpleStatementLine((imp,)))

                if not type_checking_body:
                    return updated_node

                # Ensure `from typing import TYPE_CHECKING` exists at module top
                typing_import_stmt = cst.SimpleStatementLine(
                    (cst.ImportFrom(module=cst.Name("typing"), names=(cst.ImportAlias(name=cst.Name("TYPE_CHECKING")),)),)
                )

                new_body: list[cst.CSTNode] = []
                inserted_typing_import = False

                # Strategy: place TYPE_CHECKING import after any __future__ imports and before others
                i = 0
                while i < len(updated_node.body):
                    stmt = updated_node.body[i]
                    new_body.append(stmt)
                    i += 1
                    # After initial future imports block, insert typing import if not present
                    if not inserted_typing_import:
                        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body and isinstance(stmt.body[0], cst.ImportFrom):
                            imp: cst.ImportFrom = stmt.body[0]
                            if imp.module and isinstance(imp.module, cst.Name) and imp.module.value == "__future__":
                                # Continue until we leave future block
                                continue
                        # Insert typing import if it's not already present
                        if not self.found_type_checking_import:
                            new_body.append(typing_import_stmt)
                        inserted_typing_import = True

                # Append TYPE_CHECKING block near top (after typing import that we just placed)
                type_checking_if = cst.If(
                    test=cst.Name("TYPE_CHECKING"),
                    body=cst.IndentedBlock(body=type_checking_body),
                )
                new_body.insert(1 if inserted_typing_import else 0, type_checking_if)

                return updated_node.with_changes(body=new_body)

        rewritten = module.visit(ImportRewriter())

        # 2) Inject local imports into functions for A names
        #    For each function with names, add `from <module> import Name` at top of body.
        class LocalizeRuntimeImports(cst.CSTTransformer):
            def __init__(self) -> None:
                super().__init__()
                self.class_stack: list[str] = []

            def _build_local_imports(self, func_qname: str) -> list[cst.BaseStatement]:
                names = functions_needing_local.get(func_qname)
                if not names:
                    return []
                # Group by module
                by_module: DefaultDict[str | None, list[str]] = defaultdict(list)
                for ident in sorted(names):
                    mod, _ = idx.name_to_from.get(ident, (None, None))
                    by_module[mod].append(ident)
                stmts: list[cst.BaseStatement] = []
                for mod, idents in by_module.items():
                    if not idents:
                        continue
                    import_names = [cst.ImportAlias(name=cst.Name(n)) for n in sorted(idents)]
                    stmts.append(cst.SimpleStatementLine((cst.ImportFrom(module=cst.Name(mod) if mod else None, names=tuple(import_names)),)))
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

        final_module = rewritten.visit(LocalizeRuntimeImports())

        return final_module.code

    def describe_before(self) -> str:
        return (
            "Imports are not organized by usage: runtime-in-method, class-level property types, and type-only annotations."
        )

    def describe_after(self) -> str:
        return (
            "Imports have been relocated: runtime-in-method imports are localized, class property types stay at module level, and type-only imports are moved under TYPE_CHECKING."
        )

    def description(self) -> str:
        return (
            "Relocate imports by usage. Move runtime-only symbols used inside methods into those methods; keep property-type imports at module level; move type-only imports under TYPE_CHECKING."
        )
