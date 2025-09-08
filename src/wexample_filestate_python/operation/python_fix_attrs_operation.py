from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_python_file_operation import AbstractPythonFileOperation

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class PythonFixAttrsOperation(AbstractPythonFileOperation):
    """Fix attrs usage in Python files according to standardized rules.

    Current rules:
    - Ensure @attrs.define always uses kw_only=True
    - Ensure @attr.s always uses kw_only=True

    Triggered by config: { "python": ["fix_attrs"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_FIX_ATTRS

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import libcst as cst
        from wexample_filestate_python.operation.utils.python_attrs_utils import (
            fix_attrs_kw_only,
        )

        src = cls._read_current_str_or_fail(target)
        module = cst.parse_module(src)

        modified = fix_attrs_kw_only(module)
        if modified.code == module.code:
            return None
        return modified.code

    def describe_after(self) -> str:
        return "Attrs decorators have been updated to use kw_only=True."

    def describe_before(self) -> str:
        return "Attrs decorators are missing kw_only=True parameter."

    def description(self) -> str:
        return "Ensure attrs decorators (@attrs.define, @attr.s) always use kw_only=True."
