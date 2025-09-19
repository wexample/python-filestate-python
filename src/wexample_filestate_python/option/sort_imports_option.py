from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class SortImportsConfigOption(AbstractPythonFileContentOption):
    def _apply_content_change(self, target: "TargetFileOrDirectoryType") -> str:
        """Sort Python imports using isort."""
        from isort import code
        from isort.settings import Config

        src = target.get_local_file().read()
        config = Config(profile="black")
        formatted = code(src, config=config)
        return formatted

    def describe_after(self) -> str:
        return "The Python imports have been sorted and grouped by isort."

    def describe_before(self) -> str:
        return "The Python file has unsorted or poorly grouped imports."

    def description(self) -> str:
        return "Sort and group Python imports using isort."
