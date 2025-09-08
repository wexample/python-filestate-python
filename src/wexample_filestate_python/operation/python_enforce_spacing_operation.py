from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonEnforceSpacingOperation(AbstractPythonFileOperation):
    """Enforce Python spacing rules (blank lines) across the file.

    Rules implemented now (no conflict with isort/black responsibilities):
    - File level:
      - 1 blank line after module docstring (if present)
      - 1 blank line after TYPE_CHECKING blocks (cap only)
      - Cap to at most 2 blank lines before top-level classes and functions
    - Classes:
      - 1 blank line after class docstring (cap only)
      - 1 blank line between class methods; 0 between property accessors within the same property group
      - Within method/function suites: at most 1 blank after docstring; remove leading blanks when no docstring
    - Functions:
      - Same suite rule as above for module-level functions

    NOTE: Import grouping, exact group blank lines, and other formatting areas remain
    under isort/black control and are intentionally not enforced here.

    Triggered by config: { "python": ["enforce_spacing"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ENFORCE_SPACING

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

    def describe_before(self) -> str:
        return "Blank line spacing does not follow the project rules across file, classes, and functions."

    def describe_after(self) -> str:
        return "Blank line spacing normalized according to project rules without conflicting with isort/black." 

    def description(self) -> str:
        return "Enforce standardized blank-line spacing at file, class, and function levels while deferring import and line-wrapping to isort/black."
