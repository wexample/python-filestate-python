from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class FixBlankLinesConfigOption(AbstractPythonFileContentOption):
    def _apply_content_change(self, target: "TargetFileOrDirectoryType") -> str:
        """Fix blank lines in Python files according to standardized rules.

        Current rules:
        - Remove blank lines immediately after function/method signatures
        - Remove blank lines immediately after class definitions (except after docstrings)
        - Ensure no blank lines between signature and docstring
        - Ensure no blank lines between docstring and first code line (functions only)
        - Normalize double blank lines inside function/class bodies to maximum 1 blank line
        - Class properties: no blank lines between properties except UPPERCASE to lowercase transition
        - Class properties: blank line before first method after properties section
        - Module level: 0 blank lines before module docstring
        - Module level: 1 blank line after module docstring (if present)
        - Module level: 0 blank lines before first statement (if no docstring)
        - Prevent double blank lines except: after imports, before classes/functions
        - Compatible with Black: allows blank line after class docstring
        - Compatible with Black: allows blank line before type aliases and main guard
        """
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_blank_lines_utils import (
            fix_function_blank_lines,
        )

        src = target.get_local_file().read()
        module = cst.parse_module(src)

        modified = fix_function_blank_lines(module)
        return modified.code

    def describe_after(self) -> str:
        return "Blank lines after function signatures and class definitions have been removed."

    def describe_before(self) -> str:
        return "Functions and classes have unnecessary blank lines after signatures."

    def description(self) -> str:
        return "Remove blank lines immediately after function/method signatures, class definitions, and between signatures and docstrings."
