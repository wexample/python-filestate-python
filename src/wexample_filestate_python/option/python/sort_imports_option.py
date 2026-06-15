from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@lru_cache(maxsize=1)
def _isort_setup() -> tuple:
    """Return cached (code_fn, Config) for isort with the 'black' profile.

    Both objects are imported and constructed once; subsequent calls hit
    the LRU cache, eliminating per-file import overhead for isort.code.
    """
    from isort import code as _code
    from isort.settings import Config

    return _code, Config(profile="black")


@base_class
class SortImportsOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Sort and group Python imports using isort."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Sort Python imports using isort."""
        _code, _config = _isort_setup()
        src = target.get_local_file().read()
        return _code(src, config=_config)
