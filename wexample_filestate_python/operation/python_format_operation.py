from __future__ import annotations

from typing import ClassVar

from .abstract_python_file_operation import AbstractPythonFileOperation


class PythonFormatOperation(AbstractPythonFileOperation):
    """Format Python files using Black.

    Triggered by config: { "python": ["format"] }
    """

    # Use ClassVar to avoid Pydantic treating it as a model field/private attr
    _line_length: ClassVar[int] = 88

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_FORMAT

    @classmethod
    def preview_source_change(cls, src: str) -> str:
        import black

        mode = black.Mode(line_length=cls._line_length)

        try:
            formatted = black.format_file_contents(src, fast=False, mode=mode)
            return formatted
        except black.NothingChanged:
            return src
        except Exception as e:
            raise e

    def describe_before(self) -> str:
        return "The Python file is not formatted according to Black's rules."

    def describe_after(self) -> str:
        return "The Python file has been formatted with Black."

    def description(self) -> str:
        return "Format the Python file content using Black."

    def apply(self) -> None:
        src = self.target.get_local_file().read()
        updated = self.preview_source_change(src)
        if updated != src:
            self._target_file_write(content=updated)
