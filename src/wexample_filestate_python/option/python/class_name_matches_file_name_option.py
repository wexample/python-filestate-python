from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.option.mixin.option_mixin import OptionMixin
from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class ClassNameMatchesFileNameOption(OptionMixin, AbstractConfigOption):
    def get_description(self) -> str:
        return "File name should be a pascal-case version of the class name"

    def create_required_operation(
            self, target: TargetFileOrDirectoryType, scopes: set[Scope]
    ) -> AbstractOperation | None:
        print('TODO compare file name and class name')
        print(target.get_path().name)
