from __future__ import annotations

import ast
from typing import TYPE_CHECKING, List, Type, Union

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.operation.mixin.file_manipulation_operation_mixin import (
    FileManipulationOperationMixin,
)
from wexample_filestate_python.config_option.python_config_option import (
    PythonConfigOption,
)

if TYPE_CHECKING:
    from wexample_filestate.item.item_target_directory import ItemTargetDirectory
    from wexample_filestate.item.item_target_file import ItemTargetFile


class PythonAddReturnTypesOperation(FileManipulationOperationMixin, AbstractOperation):
    """Annotate return types for functions lacking them when trivially inferable.

    Phase 1: annotate -> None, -> bool, -> str, -> int, -> float when all return
    statements in a function agree on one of these literal types.

    Triggered by config: { "python": ["add_return_types"] }.
    """

    @classmethod
    def get_scope(cls) -> Scope:
        return Scope.CONTENT

    def dependencies(self) -> List[Type["AbstractOperation"]]:
        from wexample_filestate.operation.file_create_operation import (
            FileCreateOperation,
        )

        return [FileCreateOperation]

    @staticmethod
    def applicable_option(
        target: Union["ItemTargetDirectory", "ItemTargetFile"],
        option: "AbstractConfigOption",
    ) -> bool:
        # simple, optimistic applicability as requested
        if not isinstance(option, PythonConfigOption):
            return False
        local = target.get_local_file()
        if (
            not target.is_file()
            or not local.path.exists()
            or local.path.suffix != ".py"
        ):
            return False
        value = option.get_value()
        if value is None or not value.has_item_in_list(
            PythonConfigOption.OPTION_NAME_ADD_RETURN_TYPES
        ):
            return False

        try:
            src = local.read()
            preview = _annotate_simple_returns(src)
            return preview != src
        except Exception:
            return False

    def describe_before(self) -> str:
        return "Some Python functions are missing obvious return type annotations."

    def describe_after(self) -> str:
        return "Functions have been annotated with simple return types where obvious."

    def description(self) -> str:
        return "Add simple return type annotations (None/bool/str/int/float) when trivially inferable."

    def apply(self) -> None:
        local = self.target.get_local_file()
        src = local.read()
        try:
            new_src = _annotate_simple_returns(src)
        except Exception as e:
            # If parsing or transform fails, surface clearly
            raise RuntimeError(
                "Failed to add return type annotations: " + str(e)
            ) from e
        if new_src != src:
            self._target_file_write(content=new_src)

    def undo(self) -> None:
        self._restore_target_file()


def _infer_simple_return_type(
    node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
) -> str | None:
    # Collect all return value nodes
    returns: List[ast.Return] = [n for n in ast.walk(node) if isinstance(n, ast.Return)]

    # If no return statements at all -> None
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
            # Non-literal return -> give up (phase 1)
            return None

    if len(kinds) == 1:
        return next(iter(kinds))
    # Mixed types -> give up in phase 1
    return None


def _annotate_simple_returns(src: str) -> str:
    """Add a return annotation to def lines where _infer_simple_return_type returns a type.

    We use a conservative regex rewrite limited to the function signature line to avoid
    reformatting the whole file. Works for simple cases; multi-line defs are handled by
    adding the annotation before the colon in the first line.
    """
    tree = ast.parse(src)

    # Collect function names that need annotation with their inferred type
    targets: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.returns is None
        ):
            t = _infer_simple_return_type(node)
            if t is not None:
                targets.append((node.name, t))

    if not targets:
        return src

    # Apply replacements function by function.
    import re

    new_src = src
    for func_name, rtype in targets:
        # def <name>(...) [-> ...]?:  add -> rtype before colon if missing
        pattern = rf"(def\s+{re.escape(func_name)}\s*\([^\)]*\))\s*(->\s*[^:]+)?\s*:"
        repl = rf"\1 -> {rtype}:"
        new_src, n = re.subn(pattern, repl, new_src, count=1, flags=re.MULTILINE)
        # If we didn't match (e.g., decorators with async or multiline with newline in params), try async variant
        if n == 0:
            pattern_async = rf"(async\s+def\s+{re.escape(func_name)}\s*\([^\)]*\))\s*(->\s*[^:]+)?\s*:"
            new_src = re.sub(pattern_async, repl, new_src, count=1, flags=re.MULTILINE)

    return new_src
