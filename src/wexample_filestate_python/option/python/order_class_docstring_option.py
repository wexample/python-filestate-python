from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class OrderClassDocstringOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Ensure class docstrings are at the top of each class body, preserving headers and decorators."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Ensure each class keeps header/decorators and has its docstring at the top.

        For every class definition in the module, if a class-level docstring exists but
        is not the first statement in the class suite, move it to the top (after
        decorators and the class header). Normalizes to double quotes. Avoids
        whitespace-only diffs when already correct.
        """
        import libcst as cst

        from wexample_filestate_python.utils.python_class_docstring_utils import (
            ensure_all_classes_docstring_first,
        )

        src = target.get_local_file().read()
        module = cst.parse_module(src)

        modified = ensure_all_classes_docstring_first(module)
        return modified.code
