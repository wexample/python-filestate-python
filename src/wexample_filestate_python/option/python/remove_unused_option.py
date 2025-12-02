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
        """Remove unused Python imports using autoflake."""
        from wexample_helpers.helpers.shell import shell_run
        from wexample_helpers.helpers.system import system_get_venv_bin_path

        result = shell_run(
            cmd=[
                f"{system_get_venv_bin_path()}/autoflake",
                "--stdout",
                "--remove-all-unused-imports",
                "--remove-unused-variables",
                "--expand-star-imports",
                "--remove-duplicate-keys",
                str(target.get_path()),
            ],
        )

        if result.returncode != 0:
            # Double line return is important to keep message visible event last line is erased by parent process.
            target.io.error(f"Autoflake error: {result.stderr}\n\n")
            return target.get_local_file().read()  # Return original content on error

        modified_content = result.stdout

        if not modified_content.strip():
            return target.get_local_file().read()  # Return original content if empty

        return modified_content
