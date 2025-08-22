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


class PythonRemoveUnusedImportsOperation(
    FileManipulationOperationMixin, AbstractOperation
):
    """Remove unused Python imports using autoflake.

    Triggered by config: { "python": ["remove_unused_imports"] }
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
        from autoflake import fix_code

        # Only files with the correct config option
        if not isinstance(option, PythonConfigOption):
            return False

        local_file = target.get_local_file()
        if not target.is_file() or not local_file.path.exists():
            return False

        value = option.get_value()
        if value is None or not value.has_item_in_list(
            PythonConfigOption.OPTION_NAME_REMOVE_UNUSED_IMPORTS
        ):
            return False

        src = local_file.read()
        try:
            cleaned = fix_code(
                src,
                remove_all_unused_imports=True,
                expand_star_imports=False,
                remove_duplicate_keys=False,
                remove_unused_variables=False,
            )
            return cleaned != src
        except Exception:
            return False

    def describe_before(self) -> str:
        return "The Python file contains unused imports."

    def describe_after(self) -> str:
        return "Unused imports have been removed with autoflake."

    def description(self) -> str:
        return "Remove unused imports from the Python file using autoflake."

    def apply(self) -> None:
        from autoflake import fix_code

        src = self.target.get_local_file().read()
        cleaned = fix_code(
            src,
            remove_all_unused_imports=True,
            expand_star_imports=False,
            remove_duplicate_keys=False,
            remove_unused_variables=False,
        )
        if cleaned != src:
            self._target_file_write(content=cleaned)

    def undo(self) -> None:
        self._restore_target_file()
