from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonOrderModuleClassesOperation(AbstractPythonFileOperation):
    """Order module-level classes alphabetically (A–Z) as a single contiguous block.

    Anchor strategy: the first encountered class in the original file defines the
    placement of the whole (sorted) class block. This preserves the author's
    chosen location for classes while ensuring alphabetical order.

    Triggered by config: { "python": ["order_module_classes"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ORDER_MODULE_CLASSES

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_classes_utils import (
            reorder_module_classes,
            collect_module_classes,
        )

        src = cls._read_current_str_or_fail(target)
        module = cst.parse_module(src)

        classes = collect_module_classes(module)
        if not classes:
            return None

        modified = reorder_module_classes(module)
        if modified.code == module.code:
            return None
        return modified.code

    def describe_before(self) -> str:
        return "Module-level classes are not grouped and alphabetically ordered."

    def describe_after(self) -> str:
        return "Module-level classes are grouped as a contiguous block and sorted A–Z at their original position anchor."

    def description(self) -> str:
        return "Sort module-level classes alphabetically and keep them as a single contiguous block using an anchor strategy."
