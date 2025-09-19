from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class
from .abstract_python_file_content_option import AbstractPythonFileContentOption
from .mixin.with_stdout_wrapping_mixin import WithStdoutWrappingMixin

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class FstringifyConfigOption(WithStdoutWrappingMixin, AbstractPythonFileContentOption):
    def _apply_content_change(self, target: "TargetFileOrDirectoryType") -> str:
        """Convert string formatting to f-strings using flynt."""
        from flynt.api import fstringify_code
        from flynt.state import State

        src = target.get_local_file().read()
        state = State(aggressive=False, multiline=False, len_limit=120)

        def _execute_fstringify():
            return fstringify_code(src, state=state)

        result = self._execute_and_wrap_stdout(_execute_fstringify)

        if result is None:
            return src
        return result.content

    def describe_after(self) -> str:
        return "String formatting has been converted to modern f-strings."

    def describe_before(self) -> str:
        return "The file uses legacy string formatting ('%'/format) that can be upgraded to f-strings."

    def description(self) -> str:
        return "Convert old-style string formatting to f-strings using flynt."
