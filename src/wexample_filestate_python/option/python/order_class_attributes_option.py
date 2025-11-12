from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class OrderClassAttributesOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Sort class attribute blocks with special names prioritized, preserving comments and spacing."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Sort class attributes: special first, then public A–Z, then private/protected A–Z.

        Special include __slots__, __match_args__, and inner class Config. Operates on
        contiguous attribute blocks and preserves comments attached to each attribute.
        """
        import libcst as cst

        from wexample_filestate_python.utils.python_class_attributes_utils import (
            ensure_order_class_attributes_in_module,
        )

        src = target.get_local_file().read()
        module = cst.parse_module(src)

        modified = ensure_order_class_attributes_in_module(module)
        return modified.code
