from __future__ import annotations

from typing import TYPE_CHECKING, Union, List, Type

import black

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.operation.mixin.file_manipulation_operation_mixin import (
    FileManipulationOperationMixin,
)
from wexample_filestate_python.config_option.python_config_option import PythonConfigOption

if TYPE_CHECKING:
    from wexample_filestate.item.item_target_directory import ItemTargetDirectory
    from wexample_filestate.item.item_target_file import ItemTargetFile


class PythonFormatOperation(FileManipulationOperationMixin, AbstractOperation):
    """Format Python files using Black.

    Triggered by config: { "python": ["format"] }
    """

    _line_length: int = 88

    @classmethod
    def get_scope(cls) -> Scope:
        return Scope.CONTENT

    def dependencies(self) -> List[Type["AbstractOperation"]]:
        # Ensure the file exists before formatting attempts
        from wexample_filestate.operation.file_create_operation import FileCreateOperation

        return [FileCreateOperation]

    @staticmethod
    def applicable_option(
            target: Union["ItemTargetDirectory", "ItemTargetFile"],
            option: "AbstractConfigOption",
    ) -> bool:
        # Only files, must exist, must be .py, and option must include "format"
        if not isinstance(option, PythonConfigOption):
            return False

        local_file = target.get_local_file()
        if not target.is_file() or not local_file.path.exists():
            return False
        value = option.get_value()
        if value is None:
            return False

        if not value.has_item_in_list("format"):
            return False

        mode = black.Mode()

        # Preview: check if formatting would change content
        try:

            src = local_file.read()
            # black.format_file_contents is stable for formatting a string
            formatted = black.format_file_contents(src, fast=False, mode=mode)
            return formatted != src
        except Exception:
            # Any error in preview means we skip
            return False

    def describe_before(self) -> str:
        return "The Python file is not formatted according to Black's rules."

    def describe_after(self) -> str:
        return "The Python file has been formatted with Black."

    def description(self) -> str:
        return "Format the Python file content using Black."

    def apply(self) -> None:
        # Read, format, write
        try:
            import black  # type: ignore
        except Exception as e:
            # If Black is not available at runtime, we fail explicitly so the pipeline can report it
            raise RuntimeError(
                "Black is required to run PythonFormatOperation. Please install it in the environment."
            ) from e

        mode = black.Mode(line_length=self._line_length)
        src = self.target.get_local_file().read()
        formatted = black.format_file_contents(src, fast=False, mode=mode)
        if formatted != src:
            self._target_file_write(content=formatted)

    def undo(self) -> None:
        self._restore_target_file()
