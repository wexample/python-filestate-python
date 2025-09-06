from __future__ import annotations

from typing import ClassVar, DefaultDict

from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType

from .abstract_python_file_operation import AbstractPythonFileOperation
from .utils.python_parser_import_index import PythonParserImportIndex
from .utils.python_usage_collector import PythonUsageCollector
from .utils.python_import_rewriter import PythonImportRewriter
from .utils.python_localize_runtime_imports import PythonLocalizeRuntimeImports
import libcst as cst
from collections import defaultdict


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
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_RELOCATE_IMPORTS

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        src = cls._read_current_str_or_fail(target)
        try:
            module = cst.parse_module(src)
        except Exception:
            # Fallback: keep content unchanged if parse fails.
            return src

        # Index current imports using shared utility
        idx = PythonParserImportIndex()
        module.visit(idx)

        imported_value_names: set[str] = set(idx.name_to_from.keys())

        # Usage collection
        # A: runtime usage inside function bodies
        # B: property type usage inside class body annotations
        # C: type-only annotations across module if not in A or B
        functions_needing_local: DefaultDict[str, set[str]] = defaultdict(set)  # func_qualified_name -> names
        used_in_B: set[str] = set()
        used_in_C_annot: set[str] = set()
        uc = PythonUsageCollector(
            imported_value_names=imported_value_names,
            functions_needing_local=functions_needing_local,
            used_in_B=used_in_B,
            used_in_C_annot=used_in_C_annot,
            cast_function_candidates=self._cast_function_candidates,
        )
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

        rewritten = module.visit(
            PythonImportRewriter(
                used_in_B=used_in_B,
                names_to_remove_from_module=set(used_in_A_final) | set(used_in_C_only),
                used_in_C_only=used_in_C_only,
                idx=idx,
            )
        )

        # 2) Inject local imports into functions for A names
        #    For each function with names, add `from <module> import Name` at top of body.
        final_module = rewritten.visit(
            PythonLocalizeRuntimeImports(idx=idx, functions_needing_local=functions_needing_local)
        )

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
