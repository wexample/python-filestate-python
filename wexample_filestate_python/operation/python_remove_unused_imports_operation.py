from __future__ import annotations

from .abstract_python_file_operation import AbstractPythonFileOperation


class PythonRemoveUnusedOperation(AbstractPythonFileOperation):
    """Remove unused Python imports using autoflake.

    Triggered by config: { "python": ["remove_unused_imports"] }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_REMOVE_UNUSED

    @classmethod
    def preview_source_change(cls, src: str) -> str:
        from autoflake import fix_code

        return fix_code(
            src,
            remove_all_unused_imports=True,
            expand_star_imports=True,
            remove_duplicate_keys=True,
            remove_unused_variables=True,
        )

    def describe_before(self) -> str:
        return "The Python file contains unused imports."

    def describe_after(self) -> str:
        return "Unused imports have been removed with autoflake."

    def description(self) -> str:
        return "Remove unused imports from the Python file using autoflake."

    def apply(self) -> None:
        src = self.target.get_local_file().read()
        updated = self.preview_source_change(src)
        if updated != src:
            self._target_file_write(content=updated)
