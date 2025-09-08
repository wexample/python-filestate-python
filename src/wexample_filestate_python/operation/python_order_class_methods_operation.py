from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonOrderClassMethodsOperation(AbstractPythonFileOperation):
    """Order class methods according to rules 13–17.

    - Special dunder methods in logical groups
    - Classmethods: public A–Z, then private A–Z
    - Staticmethods: public A–Z, then private A–Z
    - Properties grouped by base name (getter/setter/deleter together), groups A–Z
    - Instance methods: public A–Z, then private/protected A–Z

    Triggered by config: { "python": ["order_class_methods"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ORDER_CLASS_METHODS

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_class_methods_utils import (
            ensure_order_class_methods_in_module,
        )

        src = cls._read_current_str_or_fail(target)
        module = cst.parse_module(src)

        modified = ensure_order_class_methods_in_module(module)
        if modified.code == module.code:
            return None
        return modified.code

    def describe_after(self) -> str:
        return "Class methods have been ordered: dunders in logical sequence, then classmethods, staticmethods, properties, and instance methods."

    def describe_before(self) -> str:
        return "Class methods are not ordered: dunders, class/staticmethods, properties, instance methods."

    def description(self) -> str:
        return "Order class methods and properties according to standardized rules (13–17)."
