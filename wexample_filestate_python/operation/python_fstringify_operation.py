from __future__ import annotations

from typing import TYPE_CHECKING, List, Type, Union
import subprocess

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


class PythonFStringifyOperation(FileManipulationOperationMixin, AbstractOperation):
    """Convert string formatting to f-strings using flynt.

    Triggered by: {"python": ["fstringify"]}
    """

    @classmethod
    def get_scope(cls) -> Scope:
        return Scope.CONTENT

    def dependencies(self) -> List[Type["AbstractOperation"]]:
        from wexample_filestate.operation.file_create_operation import FileCreateOperation

        return [FileCreateOperation]

    @staticmethod
    def applicable_option(
        target: Union["ItemTargetDirectory", "ItemTargetFile"],
        option: "AbstractConfigOption",
    ) -> bool:
        if not isinstance(option, PythonConfigOption):
            return False
        lf = target.get_local_file()
        if not target.is_file() or not lf.path.exists() or lf.path.suffix != ".py":
            return False
        value = option.get_value()
        return value is not None and value.has_item_in_list(
            PythonConfigOption.OPTION_NAME_FSTRINGIFY
        )

    def apply(self) -> None:
        path = str(self.target.get_local_file().path)
        # flynt modifies files in-place
        cmd = ["flynt", "--fail-on-change", path]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # flynt returns non-zero if it changed things with --fail-on-change; re-run without it to actually apply
        if proc.returncode != 0:
            cmd_apply = ["flynt", path]
            proc2 = subprocess.run(cmd_apply, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc2.returncode != 0:
                raise RuntimeError(f"flynt failed on {path}:\n{proc2.stderr}")

    def undo(self) -> None:
        self._restore_target_file()
