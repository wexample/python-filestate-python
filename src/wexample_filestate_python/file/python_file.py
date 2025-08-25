from __future__ import annotations

from typing import ClassVar

from wexample_filestate.item.item_target_file import ItemTargetFile


class PythonFile(ItemTargetFile):
    EXTENSION_ENV: ClassVar[str] = "py"

    def _expected_file_name_extension(self) -> str | None:
        return PythonFile.EXTENSION_ENV
