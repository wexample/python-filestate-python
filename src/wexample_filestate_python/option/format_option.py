from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class FormatOption(AbstractPythonFileContentOption):
    # Use ClassVar to avoid Pydantic treating it as a model field/private attr
    _line_length: ClassVar[int] = 88

    def get_description(self) -> str:
        return "Format the Python file content using Black."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Format Python files using Black."""
        import black

        src = target.get_local_file().read()
        mode = black.Mode(line_length=self._line_length)

        try:
            formatted = black.format_file_contents(src, fast=False, mode=mode)
            return formatted
        except black.NothingChanged:
            return src
        except Exception as e:
            raise e
