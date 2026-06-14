from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class OrderModuleFunctionsOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Order module-level functions: public A–Z, then private (_*), keeping @overload groups, and move them before classes."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Order module-level functions: public A–Z, then private (_*) A–Z, before classes.

        - Keeps @overload groups attached to their implementation.
        - Preserves spacing/comments by keeping each group's first function's leading_lines.
        """
        from wexample_filestate_python.utils.cst_cache import (
            get_python_source_and_module,
        )
        from wexample_filestate_python.utils.python_functions_utils import (
            module_functions_already_ordered,
            reorder_module_functions,
        )

        src, module = get_python_source_and_module(target)

        # Fast path: module is already in the canonical order (functions before
        # classes + public A–Z → private A–Z). Skips the full rebuild + render.
        if module_functions_already_ordered(module):
            return src

        modified = reorder_module_functions(module)
        return modified.code
