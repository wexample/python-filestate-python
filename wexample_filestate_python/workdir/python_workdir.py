from typing import Optional, List, Type, TYPE_CHECKING

from wexample_filestate.config_option.children_file_factory_config_option import ChildrenFileFactoryConfigOption
from wexample_filestate.const.globals import NAME_PATTERN_NO_LEADING_DOT
from wexample_wex_addon_app.workdir.app_workdir import AppWorkdir
from wexample_config.config_value.callback_render_config_value import CallbackRenderConfigValue
from wexample_config.const.types import DictConfig
from wexample_config.options_provider.abstract_options_provider import AbstractOptionsProvider
from wexample_helpers.helpers.string import string_to_snake_case

if TYPE_CHECKING:
    from wexample_filestate.operations_provider.abstract_operations_provider import AbstractOperationsProvider
    from wexample_filestate.config_option.mixin.item_config_option_mixin import ItemTreeConfigOptionMixin


class PythonWorkdir(AppWorkdir):
    def get_options_providers(self) -> List[Type["AbstractOptionsProvider"]]:
        from wexample_filestate.options_provider.default_options_provider import DefaultOptionsProvider
        from wexample_filestate_git.options_provider.git_options_provider import GitOptionsProvider

        return [
            DefaultOptionsProvider,
            GitOptionsProvider
        ]

    def get_operations_providers(self) -> List[Type["AbstractOperationsProvider"]]:
        from wexample_filestate.operations_provider.default_operations_provider import DefaultOperationsProvider
        from wexample_filestate_git.operations_provider.git_operations_provider import GitOperationsProvider

        return [
            DefaultOperationsProvider,
            GitOperationsProvider
        ]

    @staticmethod
    def _create_package_name_snake(option: "ItemTreeConfigOptionMixin") -> str:
        import os
        return "wexample_" + string_to_snake_case(
            os.path.basename(os.path.realpath(option.get_parent_item().get_path())))

    def prepare_value(self, config: Optional[DictConfig] = None) -> DictConfig:
        from wexample_filestate.const.disk import DiskItemType
        from wexample_filestate_python.const.name_pattern import NAME_PATTERN_PYTHON_NOT_PYCACHE

        config = super().prepare_value(config)

        config.update({
            "children": [
                {
                    'name': '.gitignore',
                    'type': DiskItemType.FILE,
                    'should_exist': True,
                },
                {
                    'name': 'requirements.in',
                    'type': DiskItemType.FILE,
                    'should_exist': True,
                },
                {
                    'name': 'requirements.txt',
                    'type': DiskItemType.FILE,
                    'should_exist': True,
                },
                {
                    'name': 'tests',
                    'type': DiskItemType.DIRECTORY,
                    'should_exist': True,
                },
                # Remove unwanted files
                # Should only be created during deployment
                {
                    'name': 'build',
                    'type': DiskItemType.DIRECTORY,
                    'should_exist': False,
                },
                {
                    'name': 'dist',
                    'type': DiskItemType.DIRECTORY,
                    'should_exist': False,
                },
                {
                    'name': CallbackRenderConfigValue(raw=self._create_package_name_snake),
                    'type': DiskItemType.DIRECTORY,
                    'should_exist': True,
                    "children": [
                        ChildrenFileFactoryConfigOption(pattern={
                            "name": "__init__.py",
                            "type": DiskItemType.FILE,
                            "recursive": True,
                            "name_pattern": [NAME_PATTERN_PYTHON_NOT_PYCACHE, NAME_PATTERN_NO_LEADING_DOT],
                        })
                    ]
                }
            ]
        })

        return config
