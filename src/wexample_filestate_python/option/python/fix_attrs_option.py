from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class FixAttrsOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return (
            "Ensure attrs decorators (@attrs.define, @attr.s) always use kw_only=True."
        )

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Fix attrs usage in Python files according to standardized rules.

        Current rules:
        - Ensure @attrs.define always uses kw_only=True
        - Ensure @attr.s always uses kw_only=True
        """
        import libcst as cst

        from wexample_filestate_python.utils.python_attrs_utils import (
            fix_attrs_kw_only,
        )

        src = target.get_local_file().read()
        module = cst.parse_module(src)

        modified = fix_attrs_kw_only(module)
        return modified.code
