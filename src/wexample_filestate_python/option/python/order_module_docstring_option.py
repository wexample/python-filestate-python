from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class OrderModuleDocstringOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Move module docstring to the top of Python files. Ensures the module docstring appears as the first element before any imports or code."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Ensure module docstring is positioned at the very top of Python files.

        Moves the module docstring (if present) to be the first element in the file,
        before any imports or other code elements.
        """
        import libcst as cst

        from wexample_filestate_python.utils.python_docstring_utils import (
            find_module_docstring,
            is_module_docstring_at_top,
            move_docstring_to_top,
        )

        src = target.get_local_file().read()
        module = cst.parse_module(src)

        # Check if there's a docstring and if it needs to be moved
        docstring_node, position = find_module_docstring(module)

        if docstring_node is None:
            # No docstring found, nothing to do
            return src

        if is_module_docstring_at_top(module):
            # Check if quotes need normalization
            if len(docstring_node.body) > 0 and isinstance(
                docstring_node.body[0], cst.Expr
            ):
                expr = docstring_node.body[0]
                if isinstance(expr.value, cst.SimpleString):
                    quote = expr.value.quote
                    if quote.startswith("'''") or (
                        quote.startswith("'") and not quote.startswith('"')
                    ):
                        # Need to normalize quotes
                        from wexample_filestate_python.utils.python_docstring_utils import (
                            normalize_docstring_quotes,
                        )

                        normalized_docstring = normalize_docstring_quotes(
                            docstring_node
                        )
                        # Ensure no leading whitespace for the docstring at top
                        clean_docstring = normalized_docstring.with_changes(
                            leading_lines=[]
                        )
                        new_body = [clean_docstring] + list(module.body[1:])
                        modified_module = module.with_changes(body=new_body)
                        return modified_module.code
            # Already at top and quotes are fine
            return src

        # Move docstring to top (this also normalizes quotes)
        modified_module = move_docstring_to_top(module)
        return modified_module.code
