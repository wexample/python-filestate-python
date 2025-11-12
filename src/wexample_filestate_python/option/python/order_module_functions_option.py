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
        import libcst as cst

        from wexample_filestate_python.utils.python_functions_utils import (
            module_functions_sorted_before_classes,
            reorder_module_functions,
        )

        src = target.get_local_file().read()
        module = cst.parse_module(src)

        # Quick no-op detection: if there are no functions, or functions already sorted
        # and placed before classes, the transformation may be a noop.
        if module_functions_sorted_before_classes(module):
            # We still need to check sorting (public then private) and alpha order.
            # We will compute the transformed module and compare.
            pass

        modified = reorder_module_functions(module)
        return modified.code
