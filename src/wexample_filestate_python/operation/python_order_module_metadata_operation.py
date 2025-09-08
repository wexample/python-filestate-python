from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonOrderModuleMetadataOperation(AbstractPythonFileOperation):
    """Group and sort module metadata assignments at module level.

    Collects recognized metadata variables like `__all__`, `__version__`, `__author__`, etc.,
    groups them as a contiguous block, and sorts them alphabetically by variable name.

    Placement: after imports and `if TYPE_CHECKING:` blocks, before other module-level code.

    Triggered by config: { "python": ["order_module_metadata"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ORDER_MODULE_METADATA

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_module_metadata_utils import (
            find_module_metadata_statements,
            group_and_sort_module_metadata,
            target_index_for_module_metadata,
        )

        src = cls._read_current_str_or_fail(target)
        module = cst.parse_module(src)

        found = find_module_metadata_statements(module)
        if not found:
            return None

        # Determine if already grouped and sorted at the correct position
        indices = [i for i, _, _ in found]
        # contiguous block?
        contiguous = indices == list(range(indices[0], indices[0] + len(indices))) if indices else True
        # names sorted?
        names = [name for _, __, name in found]
        names_sorted = sorted(names, key=lambda n: n.lower())
        already_sorted = names == names_sorted
        # at correct position?
        desired_index = target_index_for_module_metadata(module)
        at_target_position = (indices and indices[0] == desired_index)

        # If everything is already correct, avoid making whitespace-only changes
        if contiguous and already_sorted and at_target_position:
            return None

        modified = group_and_sort_module_metadata(module)
        return modified.code

    def describe_after(self) -> str:
        return "Module metadata assignments are grouped together and sorted alphabetically after imports and TYPE_CHECKING."

    def describe_before(self) -> str:
        return "Module metadata assignments are scattered or unsorted at module level."

    def description(self) -> str:
        return "Group and sort module metadata (e.g., __all__, __version__, __author__) at module level with minimal spacing changes."
