from typing import TYPE_CHECKING

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate_python.config_option.python_config_option import (
    PythonConfigOption,
)

from .abstract_modernize_operation import AbstractModernizeOperation

if TYPE_CHECKING:
    from wexample_filestate.item.item_target_directory import ItemTargetDirectory
    from wexample_filestate.item.item_target_file import ItemTargetFile


class PythonModernizeTypingOperation(AbstractModernizeOperation):
    """Modernize typing syntax (PEP 585/604) to Python 3.12 style.

    Triggered by: {"python": ["modernize_typing"]}
    """

    @classmethod
    def applicable_option(
        cls,
        target: ItemTargetDirectory | ItemTargetFile,
        option: AbstractConfigOption,
    ) -> bool:
        # Validate option and target
        if not isinstance(option, PythonConfigOption):
            return False
        local_file = target.get_local_file()
        if not target.is_file() or not local_file.path.exists():
            return False
        value = option.get_value()
        if value is None or not value.has_item_in_list(
            PythonConfigOption.OPTION_NAME_MODERNIZE_TYPING
        ):
            return False

        src = local_file.read()
        updated = PythonModernizeTypingOperation._modernize_source(src)
        # Preview transformation: only applicable if change would occur
        return updated is not None and updated != src

    def describe_before(self) -> str:
        return (
            "The file uses legacy typing syntax that can be modernized for Python 3.12."
        )

    def describe_after(self) -> str:
        return "Typing syntax has been modernized to Python 3.12 style (PEP 585/604)."

    def description(self) -> str:
        return "Modernize typing syntax (PEP 585/604) using pyupgrade for Python 3.12."

    def apply(self) -> None:
        src = self.target.get_local_file().read()
        updated = self._modernize_source(src)
        if updated is not None and updated != src:
            self._target_file_write(content=updated)
