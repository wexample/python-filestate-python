from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonOrderMainGuardOperation(AbstractPythonFileOperation):
    """Ensure the `if __name__ == "__main__":` block is at the very end of the file.

    Moves any top-level main-guard blocks to be the last non-empty statement in the
    module (before trailing blank lines), preserving content and spacing as much as possible.

    Triggered by config: { "python": ["order_main_guard"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ORDER_MAIN_GUARD

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_main_guard_utils import (
            is_main_guard_at_end,
            move_main_guard_to_end,
            find_main_guard_blocks,
        )

        src = cls._read_current_str_or_fail(target)
        module = cst.parse_module(src)

        # No main guard present => nothing to do
        if not find_main_guard_blocks(module):
            return None

        # Already at end => avoid whitespace-only diffs
        if is_main_guard_at_end(module):
            return None

        modified = move_main_guard_to_end(module)
        return modified.code

    def describe_before(self) -> str:
        return "Main guard block is not positioned at the end of the file."

    def describe_after(self) -> str:
        return "Main guard block has been moved to the very end of the file."

    def description(self) -> str:
        return "Ensure the if __name__ == '__main__': block is the last non-empty statement in the module."
