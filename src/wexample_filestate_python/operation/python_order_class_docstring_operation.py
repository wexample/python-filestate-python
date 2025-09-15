from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonOrderClassDocstringOperation(AbstractPythonFileOperation):
    """Ensure each class keeps header/decorators and has its docstring at the top.

    For every class definition in the module, if a class-level docstring exists but
    is not the first statement in the class suite, move it to the top (after
    decorators and the class header). Normalizes to double quotes. Avoids
    whitespace-only diffs when already correct.

    Triggered by config: { "python": ["order_class_docstring"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ORDER_CLASS_DOCSTRING

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_class_docstring_utils import (
            ensure_all_classes_docstring_first,
        )

        src = cls._read_current_str_or_fail(target)
        module = cst.parse_module(src)

        modified = ensure_all_classes_docstring_first(module)
        if modified.code == module.code:
            return None
        return modified.code

    def describe_after(self) -> str:
        return "All class docstrings (when present) are the first statements in their classes."

    def describe_before(self) -> str:
        return (
            "Some classes have their docstring not positioned as the first statement."
        )

    def description(self) -> str:
        return "Ensure class docstrings are at the top of each class body, preserving headers and decorators."
