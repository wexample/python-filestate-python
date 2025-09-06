from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonRemoveUnusedOperation(AbstractPythonFileOperation):
    """Remove unused Python imports using autoflake.

    Triggered by config: { "python": ["remove_unused_imports"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import PythonConfigOption

        return PythonConfigOption.OPTION_NAME_REMOVE_UNUSED

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        from autoflake import fix_code

        src = cls._read_current_str_or_fail(target)
        return fix_code(
            src,
            remove_all_unused_imports=True,
            expand_star_imports=True,
            remove_duplicate_keys=True,
            remove_unused_variables=True,
        )

    def describe_before(self) -> str:
        return "The Python file contains unused imports."

    def describe_after(self) -> str:
        return "Unused imports have been removed with autoflake."

    def description(self) -> str:
        return "Remove unused imports from the Python file using autoflake."
