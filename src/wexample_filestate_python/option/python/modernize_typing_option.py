from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class ModernizeTypingOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Modernize typing syntax (PEP 585/604) using pyupgrade for Python 3.12."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Modernize typing syntax (PEP 585/604) to Python 3.12 style."""
        from pyupgrade._main import Settings, _fix_plugins

        src = target.get_local_file().read()
        settings = Settings(min_version=(3, 12))
        updated = _fix_plugins(src, settings=settings)
        return updated
