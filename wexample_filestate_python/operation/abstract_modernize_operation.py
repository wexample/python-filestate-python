from __future__ import annotations

from typing import TYPE_CHECKING, List, Type, Union
import subprocess

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.operation.mixin.file_manipulation_operation_mixin import (
    FileManipulationOperationMixin,
)

if TYPE_CHECKING:
    from wexample_filestate.item.item_target_directory import ItemTargetDirectory
    from wexample_filestate.item.item_target_file import ItemTargetFile


class AbstractModernizeOperation(FileManipulationOperationMixin, AbstractOperation):
    """Abstract base for modernizing Python source using external codemods (e.g., pyupgrade).

    Subclasses must provide pyupgrade arguments via get_pyupgrade_args().
    """

    @classmethod
    def get_scope(cls) -> Scope:
        return Scope.CONTENT

    def dependencies(self) -> List[Type["AbstractOperation"]]:
        from wexample_filestate.operation.file_create_operation import FileCreateOperation

        return [FileCreateOperation]

    # --- Hooks for subclasses ---
    def get_pyupgrade_args(self) -> List[str]:  # override
        return ["--py312-plus"]

    # --- Helpers ---
    def _run_pyupgrade_inplace(self, path_str: str) -> None:
        cmd = [
            "pyupgrade",
            *self.get_pyupgrade_args(),
            path_str,
        ]
        # Run and raise if it fails so pipeline can surface it.
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"pyupgrade failed ({proc.returncode}) on {path_str}:\n{proc.stderr}"
            )

    def apply(self) -> None:
        # Save for undo
        original = self.target.get_local_file().read()
        path = str(self.target.get_local_file().path)
        self._run_pyupgrade_inplace(path)
        updated = self.target.get_local_file().read()
        if updated != original:
            # ensure undo can restore exact content
            self._target_file_write(content=updated)

    def undo(self) -> None:
        self._restore_target_file()
