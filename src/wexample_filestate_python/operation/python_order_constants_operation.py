from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonOrderConstantsOperation(AbstractPythonFileOperation):
    """Sort flagged constant blocks (UPPER_CASE) alphabetically A–Z at module level.

    Only blocks marked by the inline flag '# filestate: python-constant-sort' are considered.
    A block is a contiguous sequence of simple UPPER_CASE assignments (no blank line between).
    Non-flagged constants and other contexts are ignored.

    Triggered by config: { "python": ["order_constants"] }
    """
    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ORDER_CONSTANTS

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_constants_utils import (
            reorder_flagged_constants_everywhere,
        )

        src = cls._read_current_str_or_fail(target)
        module = cst.parse_module(src)

        modified = reorder_flagged_constants_everywhere(module, src)
        if modified.code == module.code:
            return None
        return modified.code

    def describe_after(self) -> str:
        return "Flagged constant blocks have been sorted alphabetically without altering other code."

    def describe_before(self) -> str:
        return "Flagged constant blocks are not ordered alphabetically."

    def description(self) -> str:
        return "Sort contiguous UPPER_CASE constant blocks marked with '# filestate: python-constant-sort' alphabetically at module level."
