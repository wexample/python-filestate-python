from __future__ import annotations


class WithStdoutWrappingMixin:
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
                sys.stdout.write(stdout_content.rstrip())
                sys.stdout.write("\n")
                sys.stdout.write("\n")
            if stderr_content.strip():
                sys.stderr.write(stderr_content.rstrip())
                sys.stderr.write("\n")
                sys.stderr.write("\n")

        return result
