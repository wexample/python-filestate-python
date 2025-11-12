from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class OrderMainGuardOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Ensure the if __name__ == '__main__': block is the last non-empty statement in the module."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Ensure the `if __name__ == "__main__":` block is at the very end of the file.

        Moves any top-level main-guard blocks to be the last non-empty statement in the
        module (before trailing blank lines), preserving content and spacing as much as possible.
        """
        import libcst as cst

        from wexample_filestate_python.utils.python_main_guard_utils import (
            find_main_guard_blocks,
            is_main_guard_at_end,
            move_main_guard_to_end,
        )

        src = target.get_local_file().read()
        module = cst.parse_module(src)

        # No main guard present => nothing to do
        if not find_main_guard_blocks(module):
            return src

        # Already at end => avoid whitespace-only diffs
        if is_main_guard_at_end(module):
            return src

        modified = move_main_guard_to_end(module)
        return modified.code
