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
from wexample_filestate_python.helpers.source import source_annotate_simple_returns

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
            preview = source_annotate_simple_returns(src)
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
            new_src = source_annotate_simple_returns(src)
        except Exception as e:
            # If parsing or transform fails, surface clearly
            raise RuntimeError(
                "Failed to add return type annotations: " + str(e)
            ) from e
        if new_src != src:
            self._target_file_write(content=new_src)

    def undo(self) -> None:
        self._restore_target_file()
