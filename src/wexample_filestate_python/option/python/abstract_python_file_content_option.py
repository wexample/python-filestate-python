from __future__ import annotations

from wexample_filestate.option.abstract_file_content_option import (
    AbstractFileContentOption,
)
from wexample_helpers.decorator.base_class import base_class


@base_class
class AbstractPythonFileContentOption(AbstractFileContentOption):
    """Base class for Python file content transformation options."""

    def applicable_on_empty_content_file(self) -> bool:
        return False
