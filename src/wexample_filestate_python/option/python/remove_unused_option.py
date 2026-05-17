from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class RemoveUnusedOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Remove unused imports from the Python file using autoflake."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Remove unused Python imports using autoflake's in-process API.

        Previously shelled out to `autoflake --stdout` per file, costing ~80ms
        of subprocess + Python startup overhead each call (≈20s on a 268-file
        project).
        """
        from autoflake import fix_code

        src = target.get_local_file().read()
        try:
            return fix_code(
                src,
                remove_all_unused_imports=True,
                remove_unused_variables=True,
                expand_star_imports=True,
                remove_duplicate_keys=True,
            )
        except Exception as e:
            target.io.error(f"Autoflake error: {e}\n\n")
            return src
