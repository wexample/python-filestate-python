from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class OrderModuleMetadataOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Group and sort module metadata (e.g., __all__, __version__, __author__) at module level with minimal spacing changes."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Group and sort module metadata assignments at module level.

        Collects recognized metadata variables like `__all__`, `__version__`, `__author__`, etc.,
        groups them as a contiguous block, and sorts them alphabetically by variable name.

        Placement: after imports and `if TYPE_CHECKING:` blocks, before other module-level code.
        """
        from wexample_filestate_python.utils.cst_cache import (
            get_python_source_and_module,
        )
        from wexample_filestate_python.utils.python_module_metadata_utils import (
            find_module_metadata_statements,
            group_and_sort_module_metadata,
            target_index_for_module_metadata,
        )

        src, module = get_python_source_and_module(target)

        found = find_module_metadata_statements(module)
        if not found:
            return src

        # Determine if already grouped and sorted at the correct position
        # `found` is non-empty (early-return above), so `indices` is always non-empty
        indices = [i for i, _, _ in found]
        # contiguous block? — pairwise diff avoids list(range(...)) allocation; short-circuits
        contiguous = all(b - a == 1 for a, b in zip(indices, indices[1:]))
        # names sorted? — pairwise comparison avoids building a sorted copy; short-circuits
        names = [name for _, __, name in found]
        already_sorted = all(str.lower(a) <= str.lower(b) for a, b in zip(names, names[1:]))
        # at correct position?
        desired_index = target_index_for_module_metadata(module)
        at_target_position = indices[0] == desired_index

        # If everything is already correct, avoid making whitespace-only changes
        if contiguous and already_sorted and at_target_position:
            return src

        modified = group_and_sort_module_metadata(module)
        return modified.code
