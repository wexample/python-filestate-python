from __future__ import annotations

# Import black eagerly here (not lazily inside _run_batch_on_paths) so its
# attribute table is fully populated before any thread reads it. Modern black
# uses lazy attribute loading via module __getattr__, which is not safe under
# concurrent first-access from multiple threads (race produces spurious
# "module 'black' has no attribute 'Mode'" errors).
import black

from typing import TYPE_CHECKING, ClassVar

from wexample_filestate.option.mixin.with_batch_option_mixin import (
    WithBatchOptionMixin,
)
from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from pathlib import Path

    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class FormatOption(WithBatchOptionMixin, AbstractPythonFileContentOption):
    _line_length: ClassVar[int] = 88

    def get_description(self) -> str:
        return "Format the Python file content using Black."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        cache = self._get_or_build_batch_cache(target)
        path_key = str(target.get_path())
        if path_key in cache:
            return cache[path_key]
        return target.read_text()

    def _run_batch_on_paths(
        self,
        reference_target: TargetFileOrDirectoryType,
        paths: list[Path],
    ) -> None:
        mode = black.Mode(line_length=self._line_length)
        for path in paths:
            src = path.read_text()
            try:
                formatted = black.format_file_contents(src, fast=False, mode=mode)
                if formatted != src:
                    path.write_text(formatted)
            except black.NothingChanged:
                pass
        return None
