from __future__ import annotations

from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.operation.mixin.file_manipulation_operation_mixin import (
    FileManipulationOperationMixin,
)
from typing import TYPE_CHECKING

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate_python.config_option.python_config_option import (
    PythonConfigOption,
)

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class AbstractPythonFileOperation(FileManipulationOperationMixin, AbstractOperation):
    @classmethod
    def get_scope(cls) -> Scope:
        return Scope.CONTENT

    def undo(self) -> None:
        self._restore_target_file()

    @classmethod
    def get_option_name(cls) -> str:  # pragma: no cover - abstract contract
        raise NotImplementedError

    @classmethod
    def preview_source_change(cls, src: str) -> str:  # pragma: no cover - abstract contract
        """Return updated source if a change is needed, else return original src."""
        raise NotImplementedError

    @classmethod
    def applicable_option(
        cls, target: "TargetFileOrDirectoryType", option: "AbstractConfigOption"
    ) -> bool:
        """Generic applicability for Python file transforms controlled by a single option name."""
        # Option type
        if not isinstance(option, PythonConfigOption):
            return False

        # Target must be an existing file
        local_file = target.get_local_file()
        if not target.is_file() or not local_file.path.exists():
            return False

        # Option value must contain our specific option name
        value = option.get_value()
        if value is None or not value.has_item_in_list(cls.get_option_name()):
            return False

        # Preview transformation
        src = local_file.read()

        # Ignore empty files.
        if src.strip() == "":
            return False

        updated = cls.preview_source_change(src)
        return updated != src
