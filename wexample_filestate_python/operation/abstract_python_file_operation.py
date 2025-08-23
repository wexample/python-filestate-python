from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_existing_file_operation import (
    AbstractExistingFileOperation,
)
from wexample_filestate_python.config_option.python_config_option import (
    PythonConfigOption,
)

if TYPE_CHECKING:
    pass


class AbstractPythonFileOperation(AbstractExistingFileOperation):
    @classmethod
    def get_scope(cls) -> Scope:
        return Scope.CONTENT

    @classmethod
    def get_option_name(cls) -> str:
        raise NotImplementedError

    def applicable_for_option(
        self, option: AbstractConfigOption
    ) -> bool:
        """Generic applicability for Python file transforms controlled by a single option name."""
        # Option type
        if not isinstance(option, PythonConfigOption):
            return False

        # Option value must contain our specific option name
        value = option.get_value()
        if value is None or not value.has_item_in_list(self.get_option_name()):
            return False

        # Delegate change detection to the base helper
        return self.source_need_change(self.target)
