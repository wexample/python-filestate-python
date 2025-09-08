from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonOrderTypeCheckingBlockOperation(AbstractPythonFileOperation):
    """Move `if TYPE_CHECKING:` blocks after regular imports.

    Ensures that all top-level `if TYPE_CHECKING:` blocks are placed immediately
    after the last regular import section (or after `from __future__ import ...`
    if no regular imports exist). Keeps spacing minimal and preserves content.

    Triggered by config: { "python": ["order_type_checking_block"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ORDER_TYPE_CHECKING_BLOCK

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_type_checking_utils import (
            find_type_checking_blocks,
            move_type_checking_blocks_after_imports,
            target_index_for_type_checking,
        )

        src = cls._read_current_str_or_fail(target)
        module = cst.parse_module(src)

        blocks = find_type_checking_blocks(module)
        if not blocks:
            return None

        # Compute current positions; if already correctly positioned, no change
        current_indices = [i for i, _ in blocks]
        desired_index = target_index_for_type_checking(module)
        # Already correct if first block starts at desired index and blocks are contiguous
        contiguous = current_indices == list(range(current_indices[0], current_indices[0] + len(current_indices)))
        if contiguous and current_indices[0] == desired_index:
            return None

        modified = move_type_checking_blocks_after_imports(module)
        return modified.code

    def describe_after(self) -> str:
        return "TYPE_CHECKING blocks have been moved after regular imports with minimal spacing changes."

    def describe_before(self) -> str:
        return "TYPE_CHECKING blocks are not positioned after regular imports."

    def description(self) -> str:
        return "Move if TYPE_CHECKING blocks after imports. Keeps code layout predictable while preserving behavior."
