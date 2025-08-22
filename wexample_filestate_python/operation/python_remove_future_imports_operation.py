from typing import TYPE_CHECKING

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate_python.config_option.python_config_option import (
    PythonConfigOption,
)
from .abstract_modernize_operation import AbstractModernizeOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonRemoveFutureImportsOperation(AbstractModernizeOperation):
    """Remove now-unnecessary `from __future__ import ...` for Python 3.12.

    Triggered by: {"python": ["remove_future_imports"]}
    """

    @classmethod
    def applicable_option(
            cls,
            target: "TargetFileOrDirectoryType",
            option: "AbstractConfigOption"
    ) -> bool:
        from wexample_filestate_python.helpers.source import source_remove_future_imports

        # Validate option and target
        if not isinstance(option, PythonConfigOption):
            return False
        local_file = target.get_local_file()
        if not target.is_file() or not local_file.path.exists():
            return False
        value = option.get_value()
        if value is None or not value.has_item_in_list(
                PythonConfigOption.OPTION_NAME_REMOVE_FUTURE_IMPORTS
        ):
            return False

        src = local_file.read()
        updated = source_remove_future_imports(src)
        # Preview transformation: only applicable if change would occur
        return updated != src

    def describe_before(self) -> str:
        return "The file contains obsolete `from __future__ import ...` statements for Python 3.12."

    def describe_after(self) -> str:
        return "Obsolete `from __future__ import ...` statements have been removed."

    def description(self) -> str:
        return "Remove now-unnecessary __future__ imports using an AST-based rewrite (Python 3.12)."

    def apply(self) -> None:
        from wexample_filestate_python.helpers.source import source_remove_future_imports

        src = self.target.get_local_file().read()
        updated = source_remove_future_imports(src)
        if updated != src:
            self._target_file_write(content=updated)
