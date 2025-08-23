from __future__ import annotations

from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType
from .abstract_python_file_operation import AbstractPythonFileOperation


class PythonSortImportsOperation(AbstractPythonFileOperation):
    """Sort Python imports using isort.

    Triggered by config: { "python": ["sort_imports"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_SORT_IMPORTS

    @classmethod
    def preview_source_change(
            cls, target: TargetFileOrDirectoryType
    ) -> str | None:
        from isort import code as isort_code
        from isort.settings import Config

        src = cls._read_current_str_or_fail(target)
        config = Config(profile="black")
        formatted = isort_code(src, config=config)
        return formatted

    def describe_before(self) -> str:
        return "The Python file has unsorted or poorly grouped imports."

    def describe_after(self) -> str:
        return "The Python imports have been sorted and grouped by isort."

    def description(self) -> str:
        return "Sort and group Python imports using isort."

