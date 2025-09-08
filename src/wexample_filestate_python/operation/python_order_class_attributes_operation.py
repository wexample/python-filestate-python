from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonOrderClassAttributesOperation(AbstractPythonFileOperation):
    """Sort class attributes: special first, then public A–Z, then private/protected A–Z.

    Special include __slots__, __match_args__, and inner class Config. Operates on
    contiguous attribute blocks and preserves comments attached to each attribute.

    Triggered by config: { "python": ["order_class_attributes"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ORDER_CLASS_ATTRIBUTES

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_class_attributes_utils import (
            ensure_order_class_attributes_in_module,
        )

        src = cls._read_current_str_or_fail(target)
        module = cst.parse_module(src)

        modified = ensure_order_class_attributes_in_module(module)
        if modified.code == module.code:
            return None
        return modified.code

    def describe_after(self) -> str:
        return "Class attributes are ordered: special first, then public A–Z, then private/protected A–Z."

    def describe_before(self) -> str:
        return "Class attributes are not ordered: special, public A–Z, private A–Z."

    def description(self) -> str:
        return "Sort class attribute blocks with special names prioritized, preserving comments and spacing."
