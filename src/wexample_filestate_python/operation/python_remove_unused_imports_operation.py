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
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_REMOVE_UNUSED

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        from wexample_helpers.helpers.shell import shell_run

        return shell_run(
            cmd=["autoflake", target.get_path()],
        ).stdout.strip()

    def describe_after(self) -> str:
        return "Unused imports have been removed with autoflake."

    def describe_before(self) -> str:
        return "The Python file contains unused imports."

    def description(self) -> str:
        return "Remove unused imports from the Python file using autoflake."
