from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class AddFutureAnnotationsOption(AbstractPythonFileContentOption):
    def applicable_on_empty_content_file(self) -> bool:
        return False

    def get_description(self) -> str:
        return "Add `from __future__ import annotations` at the proper location (after shebang/encoding and module docstring)."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Add `from __future__ import annotations` if not already present."""
        src = target.get_local_file().read()

        # Fast path: already present
        if "from __future__ import annotations" in src:
            return src

        import ast
        import re

        lines = src.splitlines(keepends=True)

        # Detect shebang and encoding cookie positions
        idx = 0
        if lines and lines[0].startswith("#!"):
            idx = 1
        # Encoding cookie can be on first or second line (after shebang)
        enc_re = re.compile(r"^#.*coding[:=]\s*([-_.a-zA-Z0-9]+)")
        for i in range(idx, min(idx + 2, len(lines))):
            if enc_re.match(lines[i]):
                idx = i + 1

        # Parse to find module docstring span
        try:
            tree = ast.parse(src)
        except SyntaxError:
            # If parsing fails, be conservative: insert after header block
            insert_at = idx
        else:
            body = getattr(tree, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(getattr(body[0], "value", None), ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                # Module docstring present; insert after its end_lineno
                doc_end = getattr(body[0], "end_lineno", body[0].lineno)  # 1-based
                insert_at = max(idx, doc_end)  # line number where next stmt starts
            else:
                insert_at = idx

        # lines is 0-based; insert_at is 1-based line count from AST
        insert_index = max(0, min(len(lines), insert_at))

        # Ensure there is a newline after the inserted import if needed
        future_line = "from __future__ import annotations\n"

        # Avoid inserting duplicate blank lines: if previous line is not blank and not newline, keep
        # If there are existing future imports right after docstring, we can insert alongside them; no special handling needed
        lines.insert(insert_index, future_line)
        # If there isn't a blank line after the future import and next line is not blank, add one for readability
        j = insert_index + 1
        if j < len(lines):
            if lines[j].strip() != "":
                lines.insert(j, "\n")

        return "".join(lines)
