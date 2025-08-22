from typing import TYPE_CHECKING, Optional

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
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType
    from flynt.api import FstringifyResult


class PythonFStringifyOperation(FileManipulationOperationMixin, AbstractOperation):
    """Convert string formatting to f-strings using flynt.

    Triggered by: {"python": ["fstringify"]}
    """

    @classmethod
    def get_scope(cls) -> Scope:
        return Scope.CONTENT

    def dependencies(self) -> list[type[AbstractOperation]]:
        from wexample_filestate.operation.file_create_operation import (
            FileCreateOperation,
        )

        return [FileCreateOperation]

    @classmethod
    def applicable_option(
            cls,
            target: "TargetFileOrDirectoryType",
            option: "AbstractConfigOption"
    ) -> bool:
        if not isinstance(option, PythonConfigOption):
            return False
        local_file = target.get_local_file()
        if not target.is_file() or not local_file.path.exists():
            return False
        value = option.get_value()
        if value is None or not value.has_item_in_list(
            PythonConfigOption.OPTION_NAME_FSTRINGIFY
        ):
            return False

        src = local_file.read()

        result = cls.rectify(content=src)

        # Preview change using Flynt API (no shell)
        return result is not None and result.content != src

    @classmethod
    def rectify(cls, content: str) -> Optional["FstringifyResult"]:
        from flynt.api import fstringify_code  # type: ignore
        from flynt.state import State  # type: ignore

        state = State(
            aggressive=False,
            multiline=False,
            len_limit=120,
        )

        try:
            result = fstringify_code(content, state=state)
        except:
            result = None
        return result

    def apply(self) -> None:
        result = PythonFStringifyOperation.rectify(
            content=self.target.get_local_file().read(),
        )

        if result is not None:
            self._target_file_write(content=result.content)

    def undo(self) -> None:
        self._restore_target_file()

    def describe_before(self) -> str:
        return "The file uses legacy string formatting ('%'/format) that can be upgraded to f-strings."

    def describe_after(self) -> str:
        return "String formatting has been converted to modern f-strings."

    def description(self) -> str:
        return "Convert old-style string formatting to f-strings using flynt."
