from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonOrderSpacingOperation(AbstractPythonFileOperation):
    """Normalize blank lines (spacing) across modules, classes, and functions.

    Applies spacing rules:
    - File level: 1 blank after module docstring; 1 blank after imports & TYPE_CHECKING blocks;
      2 blanks before top-level classes/functions.
    - Class level: 1 blank after class docstring; 1 blank between methods; 0 blank between
      consecutive property members; fix method bodies to have 1 blank after docstring or 0 otherwise.
    - Function level: 1 blank after function docstring; no leading blank otherwise.

    Comments (EmptyLine with comment) are preserved and do not count as blanks.

    Triggered by config: { "python": ["order_spacing"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ORDER_SPACING

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_spacing_utils import (
            normalize_spacing_everywhere,
        )

        src = cls._read_current_str_or_fail(target)
        module = cst.parse_module(src)

        modified = normalize_spacing_everywhere(module)
        if modified.code == module.code:
            return None
        return modified.code

    def describe_after(self) -> str:
        return "Blank lines normalized across file, class, and function scopes according to spacing rules."

    def describe_before(self) -> str:
        return "Inconsistent or non-standard blank line spacing between structures."

    def description(self) -> str:
        return "Normalize blank lines between module/class/function structures while preserving comment lines."
