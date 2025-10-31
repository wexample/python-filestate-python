from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class OrderTypeCheckingBlockOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Move if TYPE_CHECKING blocks after imports. Keeps code layout predictable while preserving behavior."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Move `if TYPE_CHECKING:` blocks after regular imports.

        Ensures that all top-level `if TYPE_CHECKING:` blocks are placed immediately
        after the last regular import section (or after `from __future__ import ...`
        if no regular imports exist). Keeps spacing minimal and preserves content.
        """
        import libcst as cst

        from wexample_filestate_python.utils.python_type_checking_utils import (
            find_type_checking_blocks,
            move_type_checking_blocks_after_imports,
            target_index_for_type_checking,
        )

        src = target.get_local_file().read()
        module = cst.parse_module(src)

        blocks = find_type_checking_blocks(module)
        if not blocks:
            return src

        # Compute current positions; if already correctly positioned, no change
        current_indices = [i for i, _ in blocks]
        desired_index = target_index_for_type_checking(module)
        # Already correct if first block starts at desired index and blocks are contiguous
        contiguous = current_indices == list(
            range(current_indices[0], current_indices[0] + len(current_indices))
        )
        if contiguous and current_indices[0] == desired_index:
            return src

        modified = move_type_checking_blocks_after_imports(module)
        return modified.code
