from __future__ import annotations

from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType
from .abstract_python_file_operation import AbstractPythonFileOperation


class PythonAddReturnTypesOperation(AbstractPythonFileOperation):
    """Annotate return types for functions lacking them when trivially inferable.

    Phase 1: annotate -> None, -> bool, -> str, -> int, -> float when all return
    statements in a function agree on one of these literal types.

    Triggered by config: { "python": ["add_return_types"] }.
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ADD_RETURN_TYPES

    @classmethod
    def preview_source_change(
            cls, target: TargetFileOrDirectoryType
    ) -> str | None:
        """Add a return annotation to def lines where a simple literal type is inferable.

        Logic is inlined here (previously in helpers.source.source_annotate_simple_returns).
        """
        import ast
        import re
        src = cls._read_current_str_or_fail(target)

        def infer_simple_return_type(
            node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> str | None:
            returns: list[ast.Return] = [
                n for n in ast.walk(node) if isinstance(n, ast.Return)
            ]
            if not returns:
                return "None"
            kinds: set[str] = set()
            for ret in returns:
                val = ret.value
                if val is None:
                    kinds.add("None")
                elif isinstance(val, ast.Constant):
                    if isinstance(val.value, bool):
                        kinds.add("bool")
                    elif isinstance(val.value, str):
                        kinds.add("str")
                    elif isinstance(val.value, int):
                        kinds.add("int")
                    elif isinstance(val.value, float):
                        kinds.add("float")
                    elif val.value is None:
                        kinds.add("None")
                    else:
                        return None
                else:
                    return None
            if len(kinds) == 1:
                return next(iter(kinds))
            return None

        tree = ast.parse(src)

        targets: list[tuple[str, str]] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.returns is None
            ):
                t = infer_simple_return_type(node)
                if t is not None:
                    targets.append((node.name, t))

        if not targets:
            return src

        new_src = src
        for func_name, rtype in targets:
            pattern = (
                rf"(def\s+{re.escape(func_name)}\s*\([^\)]*\))\s*(->\s*[^:]+)?\s*:"
            )
            repl = rf"\1 -> {rtype}:"
            new_src, n = re.subn(pattern, repl, new_src, count=1, flags=re.MULTILINE)
            if n == 0:
                pattern_async = rf"(async\s+def\s+{re.escape(func_name)}\s*\([^\)]*\))\s*(->\s*[^:]+)?\s*:"
                new_src = re.sub(
                    pattern_async, repl, new_src, count=1, flags=re.MULTILINE
                )

        return new_src

    def describe_before(self) -> str:
        return "Some Python functions are missing obvious return type annotations."

    def describe_after(self) -> str:
        return "Functions have been annotated with simple return types where obvious."

    def description(self) -> str:
        return "Add simple return type annotations (None/bool/str/int/float) when trivially inferable."

