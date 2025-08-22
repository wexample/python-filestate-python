from __future__ import annotations

from .abstract_python_file_operation import AbstractPythonFileOperation


class PythonFStringifyOperation(AbstractPythonFileOperation):
    """Convert string formatting to f-strings using flynt.

    Triggered by: {"python": ["fstringify"]}
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_FSTRINGIFY

    @classmethod
    def preview_source_change(cls, src: str) -> str:
        from flynt.api import fstringify_code  # type: ignore
        from flynt.state import State  # type: ignore

        state = State(aggressive=False, multiline=False, len_limit=120)
        try:
            result = fstringify_code(src, state=state)
        except Exception:
            return src
        if result is None:
            return src
        return result.content

    def apply(self) -> None:
        src = self.target.get_local_file().read()
        updated = self.preview_source_change(src)
        if updated != src:
            self._target_file_write(content=updated)

    def describe_before(self) -> str:
        return "The file uses legacy string formatting ('%'/format) that can be upgraded to f-strings."

    def describe_after(self) -> str:
        return "String formatting has been converted to modern f-strings."

    def description(self) -> str:
        return "Convert old-style string formatting to f-strings using flynt."
