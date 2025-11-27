from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.option.mixin.option_mixin import OptionMixin
from wexample_helpers.classes.abstract_method import abstract_method
from wexample_helpers.decorator.base_class import base_class

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class AbstractPythonFileContentOption(OptionMixin, AbstractConfigOption):
    @staticmethod
    def get_raw_value_allowed_type() -> Any:
        return bool

    def create_required_operation(
        self, target: TargetFileOrDirectoryType, scopes: set[Scope]
    ) -> AbstractOperation | None:
        from wexample_filestate.operation.file_write_operation import FileWriteOperation

        """Create FileWriteOperation if add_future_annotations is enabled and needed."""
        # Get current content
        current_content = target.get_local_file().read()

        # Apply add_future_annotations transformation
        new_content = self._apply_content_change(target=target)

        # If content changed, create FileWriteOperation
        if new_content != current_content:
            return FileWriteOperation(
                option=self,
                target=target,
                content=new_content,
                description=self.get_description(),
            )

        return None

    @abstract_method
    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> None:
        pass
