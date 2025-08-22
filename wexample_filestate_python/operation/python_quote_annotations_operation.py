from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.operation.mixin.file_manipulation_operation_mixin import (
    FileManipulationOperationMixin,
)
from wexample_filestate_python.config_option.python_config_option import (
    PythonConfigOption,
)

if TYPE_CHECKING:
    from wexample_filestate.item.item_target_directory import ItemTargetDirectory
    from wexample_filestate.item.item_target_file import ItemTargetFile


class PythonQuoteAnnotationsOperation(FileManipulationOperationMixin, AbstractOperation):
    """Quote all type annotations (params, returns, variables) using LibCST.

    Triggered by config: { "python": ["quote_annotations"] }
    """

    @classmethod
    def get_scope(cls) -> Scope:
        return Scope.CONTENT

    def dependencies(self) -> list[type[AbstractOperation]]:
        from wexample_filestate.operation.file_create_operation import (
            FileCreateOperation,
        )

        return [FileCreateOperation]

    @classmethod
    def applicable_option(
            cls,
            target: ItemTargetDirectory | ItemTargetFile,
            option: AbstractConfigOption,
    ) -> bool:
        from wexample_filestate_python.helpers.source import source_quote_annotations

        if not isinstance(option, PythonConfigOption):
            return False
        local_file = target.get_local_file()
        if not target.is_file() or not local_file.path.exists():
            return False
        value = option.get_value()
        if value is None or not value.has_item_in_list(
                PythonConfigOption.OPTION_NAME_QUOTE_ANNOTATIONS
        ):
            return False

        src = local_file.read()
        updated = source_quote_annotations(src)
        return updated != src

    def describe_before(self) -> str:
        return "The Python file contains unquoted type annotations."

    def describe_after(self) -> str:
        return "All type annotations have been converted to strings."

    def description(self) -> str:
        return "Quote all type annotations (arguments, returns, variables) using LibCST."

    def apply(self) -> None:
        from wexample_filestate_python.helpers.source import source_quote_annotations

        src = self.target.get_local_file().read()
        updated = source_quote_annotations(src)
        if updated != src:
            self._target_file_write(content=updated)

    def undo(self) -> None:
        self._restore_target_file()
