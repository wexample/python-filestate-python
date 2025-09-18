from __future__ import annotations

from typing import Any, TYPE_CHECKING

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_helpers.decorator.base_class import base_class

if TYPE_CHECKING:
    from wexample_filestate.operation.abstract_operation import AbstractOperation
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class AddFutureAnnotationsConfigOption(AbstractConfigOption):
    @staticmethod
    def get_raw_value_allowed_type() -> Any:
        return bool

    def create_required_operation(self, target: "TargetFileOrDirectoryType") -> "AbstractOperation | None":
        """Create FileWriteOperation if add_future_annotations is enabled and needed."""
        # Check if this option is enabled
        if not self.is_true():
            return None
        
        # Only process Python files
        if not target.is_file() or not target.get_item_name().endswith('.py'):
            return None
        
        # Get current content
        current_content = self._read_current_content(target)
        if current_content is None:
            return None
        
        # Apply add_future_annotations transformation
        new_content = self._add_future_annotations(current_content)
        
        # If content changed, create FileWriteOperation
        if new_content != current_content:
            return self._create_file_write_operation(target=target, content=new_content)
        
        return None

    def _read_current_content(self, target: "TargetFileOrDirectoryType") -> str | None:
        """Read current file content, return None if file doesn't exist."""
        if not target.source or not target.source.get_path().exists():
            return None
        return target.get_local_file().read()

    def _create_file_write_operation(self, **kwargs):
        from wexample_filestate.operation.file_write_operation import FileWriteOperation
        
        return FileWriteOperation(**kwargs)

    def _add_future_annotations(self, src: str) -> str:
        """Add `from __future__ import annotations` if not already present.
        
        Migrated logic from PythonAddFutureAnnotationsOperation.
        """
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
