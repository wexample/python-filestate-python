from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonOrderIterableItemsOperation(AbstractPythonFileOperation):
    """Sort items inside flagged iterable literals (lists, and simple dicts where applicable).

    Looks for the inline flag '# filestate: python-iterable-sort' and sorts the following
    contiguous block of iterable items alphabetically (case-insensitive), preserving
    indentation and punctuation. Intended primarily for list literals written one-item-per-line.

    Triggered by config: { "python": ["order_iterable_items"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ORDER_ITERABLE_ITEMS

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        from wexample_filestate_python.operation.utils.python_iterable_utils import (
            reorder_flagged_iterables,
        )

        src = cls._read_current_str_or_fail(target)
        modified = reorder_flagged_iterables(src)
        if modified == src:
            return None
        return modified

    def describe_before(self) -> str:
        return "Flagged iterable blocks are not ordered alphabetically."

    def describe_after(self) -> str:
        return "Flagged iterable blocks have been sorted alphabetically while preserving formatting."

    def description(self) -> str:
        return "Sort items inside iterable literals following the '# filestate: python-iterable-sort' flag (primarily lists with one-item-per-line)."
