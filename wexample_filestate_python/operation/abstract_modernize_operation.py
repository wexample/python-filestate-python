from __future__ import annotations

from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.operation.mixin.file_manipulation_operation_mixin import (
    FileManipulationOperationMixin,
)


class AbstractModernizeOperation(FileManipulationOperationMixin, AbstractOperation):
    """Abstract base for modernizing Python source in-memory.

    Uses the pyupgrade library programmatically (no shell) to preview and apply
    transformations. Subclasses should override `get_min_version()` to control
    the target Python version for upgrades.
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
    def get_min_version(cls) -> tuple[int, int]:
        """Return the minimum target Python version as a (major, minor) tuple.

        Defaults to (3, 12). Subclasses can override.
        """
        return (3, 12)

    @classmethod
    def _modernize_source(cls, src: str) -> str | None:
        from pyupgrade._main import Settings, _fix_plugins  # type: ignore

        settings = Settings(min_version=cls.get_min_version())
        return _fix_plugins(src, settings=settings)

    def undo(self) -> None:
        self._restore_target_file()
