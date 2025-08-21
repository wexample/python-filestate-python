from __future__ import annotations

from typing import TYPE_CHECKING, List, Type, Union

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate_python.config_option.python_config_option import PythonConfigOption
from .abstract_modernize_operation import AbstractModernizeOperation

if TYPE_CHECKING:
    from wexample_filestate.item.item_target_directory import ItemTargetDirectory
    from wexample_filestate.item.item_target_file import ItemTargetFile


class PythonCleanupPy2CompatOperation(AbstractModernizeOperation):
    """Remove Python 2 compatibility leftovers using pyupgrade.

    Triggered by: {"python": ["cleanup_py2_compat"]}
    """

    @classmethod
    def applicable_option(
        cls,
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
            PythonConfigOption.OPTION_NAME_CLEANUP_PY2_COMPAT
        )

    def get_pyupgrade_args(self) -> List[str]:
        # Target modern python; pyupgrade will drop py2 shims, old patterns, future imports unnecessary, etc.
        return ["--py312-plus"]

    def describe_before(self) -> str:
        return "The file may contain outdated Python 2 compatibility shims or legacy patterns."

    def describe_after(self) -> str:
        return "Python 2 compatibility code and legacy patterns have been removed for Python 3.12."

    def description(self) -> str:
        return "Clean up Python 2 compatibility and legacy patterns using pyupgrade for Python 3.12."
