from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonNormalizeSpacingOperation(AbstractPythonFileOperation):
    """Normalize blank lines according to Python spacing rules.

    Applies exact spacing requirements (not min/max) for:
    - File level: module docstring, imports, TYPE_CHECKING blocks
    - Classes: definitions, docstrings, properties, methods
    - Functions: definitions, docstrings, control structures
    - Comments are preserved and don't affect spacing rules
    - Blank lines have no indentation (empty strings)

    Triggered by config: { "python": ["normalize_spacing"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_NORMALIZE_SPACING

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
        return "Blank lines have been normalized according to Python spacing rules."

    def describe_before(self) -> str:
        return "Blank line spacing does not follow Python conventions."

    def description(self) -> str:
        return "Normalize blank lines between structures according to exact Python spacing rules, preserving comments."
