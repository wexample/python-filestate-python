from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class OrderIterableItemsOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Sort items inside iterable literals following the '# filestate: python-iterable-sort' flag (primarily lists with one-item-per-line)."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Sort items inside flagged iterable literals (lists, and simple dicts where applicable).

        Looks for the inline flag '# filestate: python-iterable-sort' and sorts the following
        contiguous block of iterable items alphabetically (case-insensitive), preserving
        indentation and punctuation. Intended primarily for list literals written one-item-per-line.
        """
        from wexample_filestate_python.utils.python_iterable_utils import (
            reorder_flagged_iterables,
        )

        src = target.get_local_file().read()
        modified = reorder_flagged_iterables(src)
        return modified
