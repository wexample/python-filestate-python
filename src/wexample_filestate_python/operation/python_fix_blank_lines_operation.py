from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonFixBlankLinesOperation(AbstractPythonFileOperation):
    """Fix blank lines in Python files according to standardized rules.

    Current rules:
    - Remove blank lines immediately after function/method signatures
    - Ensure no blank lines between signature and docstring
    - Ensure no blank lines between docstring and first code line
    - Module level: 0 blank lines before module docstring
    - Module level: 1 blank line after module docstring (if present)
    - Module level: 0 blank lines before first statement (if no docstring)
    - No double blank lines except: after imports, before classes, before module functions

    Triggered by config: { "python": ["fix_blank_lines"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_FIX_BLANK_LINES

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_blank_lines_utils import (
            fix_function_blank_lines,
        )

        src = cls._read_current_str_or_fail(target)
        module = cst.parse_module(src)

        modified = fix_function_blank_lines(module)
        if modified.code == module.code:
            return None
        return modified.code

    def describe_after(self) -> str:
        return "Blank lines after function signatures have been removed."

    def describe_before(self) -> str:
        return "Functions have unnecessary blank lines after signatures."

    def description(self) -> str:
        return "Remove blank lines immediately after function/method signatures and between signatures and docstrings."
