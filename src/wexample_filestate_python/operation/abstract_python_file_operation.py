from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.operation.abstract_existing_file_operation import (
    AbstractExistingFileOperation,
)

if TYPE_CHECKING:
    from wexample_config.config_option.abstract_config_option import (
        AbstractConfigOption,
    )
    from wexample_filestate.enum.scopes import Scope


class AbstractPythonFileOperation(AbstractExistingFileOperation):
    @classmethod
    def get_option_name(cls) -> str:
        raise NotImplementedError

    @classmethod
    def get_scope(cls) -> Scope:
        from wexample_filestate.enum.scopes import Scope

        return Scope.CONTENT

    @classmethod
    def _execute_and_wrap_stdout(cls, callback):
        """Execute a callback and wrap any stdout/stderr output with additional newlines.

        This ensures that output from external tools doesn't interfere with progress indicators
        by adding a newline after any captured output.

        Args:
            callback: Function to execute that may produce stdout/stderr output

        Returns:
            The return value of the callback function
        """
        import io
        import sys

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        sys.stdout = captured_stdout
        sys.stderr = captured_stderr

        try:
            result = callback()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            stdout_content = captured_stdout.getvalue()
            stderr_content = captured_stderr.getvalue()

            if stdout_content.strip():
                print(stdout_content.rstrip())
                print()
            if stderr_content.strip():
                print(stderr_content.rstrip(), file=sys.stderr)
                print(file=sys.stderr)

        return result

    def applicable_for_option(self, option: AbstractConfigOption) -> bool:
        """Generic applicability for Python file transforms controlled by a single option name."""
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        # Option type
        if not isinstance(option, PythonConfigOption):
            return False

        # Option value must contain our specific option name
        value = option.get_value()
        if value is None or not value.has_item_in_list(self.get_option_name()):
            return False

        # Delegate change detection to the base helper
        return self.source_need_change(self.target)
