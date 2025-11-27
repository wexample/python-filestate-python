from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class OrderClassMethodsOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Order class methods and properties according to standardized rules."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Order class methods according to rules 13–17.

        - Special dunder methods in logical groups
        - Classmethods: public A–Z, then private A–Z
        - Staticmethods: public A–Z, then private A–Z
        - Properties grouped by base name (getter/setter/deleter together), groups A–Z
        - Instance methods: public A–Z, then private/protected A–Z
        """
        import libcst as cst

        from wexample_filestate_python.utils.python_class_methods_utils import (
            ensure_order_class_methods_in_module,
        )

        src = target.get_local_file().read()
        module = cst.parse_module(src)

        modified = ensure_order_class_methods_in_module(module)
        return modified.code
