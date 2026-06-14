from __future__ import annotations

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
        if not paths:
            return
        # Black is loaded lazily here. Thread-safety: dry_run()/apply() always
        # call _prepare_options() before parallel inspection, which runs this
        # method in the main thread first — so by the time worker threads run,
        # the module is fully loaded and there is no concurrent first-import
        # race on its lazy attribute table.
        import black

        mode = black.Mode(line_length=self._line_length)
        for path in paths:
            src = path.read_text(encoding="utf-8")
            try:
                formatted = black.format_file_contents(src, fast=False, mode=mode)
                if formatted != src:
                    path.write_text(formatted, encoding="utf-8")
            except black.NothingChanged:
                pass
