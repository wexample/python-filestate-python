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
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonSortImportsOperation(FileManipulationOperationMixin, AbstractOperation):
    """Sort Python imports using isort.

    Triggered by config: { "python": ["sort_imports"] }
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
        cls, target: TargetFileOrDirectoryType, option: AbstractConfigOption
    ) -> bool:
        from isort import code as isort_code
        from isort.settings import Config

        # Only files, must exist, must be .py, and option must include "sort_imports"
        if not isinstance(option, PythonConfigOption):
            return False

        local_file = target.get_local_file()
        if not target.is_file() or not local_file.path.exists():
            return False

        value = option.get_value()
        if value is None:
            return False

        if not value.has_item_in_list(PythonConfigOption.OPTION_NAME_SORT_IMPORTS):
            return False

        try:
            src = local_file.read()
            config = Config(profile="black")
            formatted = isort_code(src, config=config)
            return formatted != src
        except Exception:
            return False

    def describe_before(self) -> str:
        return "The Python file has unsorted or poorly grouped imports."

    def describe_after(self) -> str:
        return "The Python imports have been sorted and grouped by isort."

    def description(self) -> str:
        return "Sort and group Python imports using isort."

    def apply(self) -> None:
        from isort import code as isort_code  # type: ignore
        from isort.settings import Config

        src = self.target.get_local_file().read()
        config = Config(profile="black")
        formatted = isort_code(src, config=config)
        if formatted != src:
            self._target_file_write(content=formatted)

    def undo(self) -> None:
        self._restore_target_file()
