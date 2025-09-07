from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonOrderModuleDocstringOperation(AbstractPythonFileOperation):
    """Ensure module docstring is positioned at the very top of Python files.

    Moves the module docstring (if present) to be the first element in the file,
    before any imports or other code elements.

    Triggered by config: { "python": ["order_module_docstring"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ORDER_MODULE_DOCSTRING

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        # TODO: Implement module docstring ordering
        # 
        # Corrections to apply:
        # 1. Detect if file has a module docstring (triple-quoted string at module level)
        # 2. If docstring exists but is not at the very top, move it to position 1
        # 3. nope : Ensure docstring comes before any imports, constants, or other code
        # 4. Preserve the exact content and formatting of the docstring
        # 5. Handle both single-line and multi-line docstrings
        # 6. nope, convert to double : Support both """ and ''' quote styles
        
        return None

    def describe_before(self) -> str:
        return "Module docstring is not positioned at the top of the file."

    def describe_after(self) -> str:
        return "Module docstring has been moved to the top of the file."

    def description(self) -> str:
        return "Move module docstring to the top of Python files. Ensures the module docstring appears as the first element before any imports or code."
