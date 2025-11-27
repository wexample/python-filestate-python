from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class RelocateImportsOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Keep module-level and type imports at the top; move runtime-only imports used inside methods into those methods."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Relocate imports according to usage categories:

        Rules:
        - runtime_local (formerly A): names used at runtime inside functions/methods
          (e.g., return MyClass(), typing.cast(x, MyClass)).
          -> import locally at the top of each function using it.
        - class_level (formerly B): names required at class-definition time
          (e.g., class attribute annotations, base class references).
          -> keep/import at module top level.
        - type_only (formerly C): names used only in type annotations (function
          params/returns, module-level annotations) and not in runtime_local or class_level.
          -> move under `if TYPE_CHECKING:` at module top (add "from typing import TYPE_CHECKING"
             if missing). Files already have `from __future__ import annotations`.
        """
        from collections import defaultdict
        from typing import DefaultDict

        import libcst as cst

        from wexample_filestate_python.utils.relocate_imports.python_import_rewriter import (
            PythonImportRewriter,
        )
        from wexample_filestate_python.utils.relocate_imports.python_localize_runtime_imports import (
            PythonLocalizeRuntimeImports,
        )
        from wexample_filestate_python.utils.relocate_imports.python_parser_import_index import (
            PythonParserImportIndex,
        )
        from wexample_filestate_python.utils.relocate_imports.python_runtime_symbol_collector import (
            PythonRuntimeSymbolCollector,
        )
        from wexample_filestate_python.utils.relocate_imports.python_usage_collector import (
            PythonUsageCollector,
        )

        src = target.get_local_file().read()
        module = cst.parse_module(src)

        # Index current imports using shared utility
        idx = PythonParserImportIndex()
        module.visit(idx)

        imported_value_names: set[str] = set(idx.name_to_from.keys())

        # Usage collection
        # runtime_local: usage inside function bodies
        # class_level: usage inside class body annotations (needed at definition time)
        # type_only: type-only annotations across module if not in runtime_local or class_level
        functions_needing_local: DefaultDict[str, set[str]] = defaultdict(
            set
        )  # func_qualified_name -> names
        class_level_names: set[str] = set()
        type_annotation_names: set[str] = set()
        cast_type_names_anywhere: set[str] = set()
        uc = PythonUsageCollector(
            imported_value_names=imported_value_names,
            functions_needing_local=functions_needing_local,
            used_in_B=class_level_names,
            used_in_C_annot=type_annotation_names,
            cast_type_names_anywhere=cast_type_names_anywhere,
            idx=idx,
        )
        module.visit(uc)

        # Conservative fallback: collect any imported names used in non-annotation expressions
        rsc = PythonRuntimeSymbolCollector(imported_value_names=imported_value_names)
        module.visit(rsc)
        runtime_used_anywhere: set[str] = rsc.runtime_used_anywhere

        # Resolve categories
        runtime_local_all: set[str] = (
            set().union(*functions_needing_local.values())
            if functions_needing_local
            else set()
        )
        # class_level has priority over runtime_local: if a name is class-level, we do NOT local-import it
        runtime_local_final: set[str] = {
            n for n in runtime_local_all if n not in class_level_names
        }
        # type_only = in type annotations but not runtime_local_final or class_level
        # Exclude any names that appear in cast() type expressions anywhere from C-only,
        # since casts require runtime availability of the symbol.
        type_only_names: set[str] = {
            n
            for n in type_annotation_names
            if n not in runtime_local_final
            and n not in class_level_names
            and n not in cast_type_names_anywhere
            and n not in runtime_used_anywhere
        }

        # Names to include under TYPE_CHECKING:
        # Use all names that appear in annotations (params/returns/module-level), excluding class-level.
        # Then subtract names that are already locally imported inside some function where
        # they are used (to avoid redundant TYPE_CHECKING imports when a function-scoped
        # import suffices, e.g., `from multiprocessing import Queue` inside a method).
        annotation_names_candidate: set[str] = {
            n for n in type_annotation_names if n not in class_level_names
        }

        # Collect names imported locally inside functions anywhere in the module
        class _LocalImportNameCollector(cst.CSTVisitor):
            def __init__(self) -> None:
                self.stack: list[str] = []
                self.local_imported: set[str] = set()

            def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # type: ignore[override]
                self.stack.append(node.name.value)
                return True

            def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # type: ignore[override]
                self.stack.pop()

            def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:  # type: ignore[override]
                if not self.stack:
                    return True
                if node.names is None or isinstance(node.names, cst.ImportStar):
                    return True
                for alias in node.names:
                    if isinstance(alias, cst.ImportAlias) and isinstance(
                        alias.name, cst.Name
                    ):
                        name = (
                            alias.asname.name.value
                            if alias.asname
                            else alias.name.value
                        )
                        self.local_imported.add(name)
                return True

        lic = _LocalImportNameCollector()
        module.visit(lic)
        type_only_for_block: set[str] = annotation_names_candidate - lic.local_imported

        # For names used inside cast() anywhere in the module:
        # - do NOT auto-add to TYPE_CHECKING (unless also in annotations via type_only_for_block)
        # - remove module-level import unless also class_level or runtime_used_anywhere
        # Exclude names used at runtime at module level (e.g., TerminalColor.RED in dict values)
        names_to_remove_from_module = (
            (set(runtime_local_final) - runtime_used_anywhere)
            | set(type_only_names)
            | (
                set(cast_type_names_anywhere)
                - set(class_level_names)
                - runtime_used_anywhere
            )
        )

        # Do not add to TYPE_CHECKING if the name's module-level import is kept
        kept_module_imports: set[str] = {
            n for n in imported_value_names if n not in names_to_remove_from_module
        }
        used_in_C_only_final: set[str] = set(type_only_for_block) - kept_module_imports

        # Debug summary removed
        rewritten = module.visit(
            PythonImportRewriter(
                used_in_B=class_level_names,
                names_to_remove_from_module=names_to_remove_from_module,
                used_in_C_only=used_in_C_only_final,
                idx=idx,
            )
        )

        # 2) Inject local imports into functions for runtime_local names
        #    For each function with names, add `from <module> import Name` at top of body.
        final_module = rewritten.visit(
            PythonLocalizeRuntimeImports(
                idx=idx,
                functions_needing_local=functions_needing_local,
                # Do not skip cast-used names so they are localized per method.
                skip_local_names=set(class_level_names),
            )
        )

        return final_module.code
