from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class OrderConstantsOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Sort contiguous UPPER_CASE constant blocks marked with '# filestate: python-constant-sort' alphabetically at module level."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Sort flagged constant blocks (UPPER_CASE) alphabetically A–Z at module level.

        Only blocks marked by the inline flag '# filestate: python-constant-sort' are considered.
        A block is a contiguous sequence of simple UPPER_CASE assignments (no blank line between).
        Non-flagged constants and other contexts are ignored.
        """
        import libcst as cst

        from wexample_filestate_python.utils.python_constants_utils import (
            reorder_flagged_constants_everywhere,
        )

        src = target.get_local_file().read()
        module = cst.parse_module(src)

        modified = reorder_flagged_constants_everywhere(module, src)
        return modified.code
