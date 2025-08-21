from __future__ import annotations

from typing import TYPE_CHECKING, List, Type, Union

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate_python.config_option.python_config_option import PythonConfigOption
from .abstract_modernize_operation import AbstractModernizeOperation

if TYPE_CHECKING:
    from wexample_filestate.item.item_target_directory import ItemTargetDirectory
    from wexample_filestate.item.item_target_file import ItemTargetFile


class PythonModernizeTypingOperation(AbstractModernizeOperation):
    """Modernize typing syntax (PEP 585/604) to Python 3.12 style.

    Triggered by: {"python": ["modernize_typing"]}
    """

    @staticmethod
    def applicable_option(
        target: Union["ItemTargetDirectory", "ItemTargetFile"],
        option: "AbstractConfigOption",
    ) -> bool:
        if not isinstance(option, PythonConfigOption):
            return False
        lf = target.get_local_file()
        if not target.is_file() or not lf.path.exists():
            return False
        value = option.get_value()
        return value is not None and value.has_item_in_list(
            PythonConfigOption.OPTION_NAME_MODERNIZE_TYPING
        )

    def get_pyupgrade_args(self) -> List[str]:
        # pyupgrade will handle PEP585/604 under --py312-plus
        return ["--py312-plus"]

    def describe_before(self) -> str:
        return "The file uses legacy typing syntax that can be modernized for Python 3.12."

    def describe_after(self) -> str:
        return "Typing syntax has been modernized to Python 3.12 style (PEP 585/604)."

    def description(self) -> str:
        return "Modernize typing syntax (PEP 585/604) using pyupgrade for Python 3.12."
