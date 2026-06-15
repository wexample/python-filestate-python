from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@lru_cache(maxsize=1)
def _isort_black_config() -> Config:
    """Return a cached isort Config for the 'black' profile."""
    from isort.settings import Config

    return Config(profile="black")


@base_class
class SortImportsOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Sort and group Python imports using isort."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Sort Python imports using isort."""
        from isort import code

        src = target.get_local_file().read()
        return code(src, config=_isort_black_config())
