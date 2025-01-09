from typing import Optional, List

from wexample_filestate_python.workdir.python_workdir import PythonWorkdir
from wexample_config.const.types import DictConfig
from wexample_helpers.helpers.array import array_dict_get_by


class PythonPackageWorkdir(PythonWorkdir):
    def prepare_value(self, config: Optional[DictConfig] = None) -> DictConfig:
        from wexample_filestate.const.disk import DiskItemType

        config = super().prepare_value(config)

        # Retrieve the '.gitignore' configuration or create it if it doesn't exist
        config_gitignore = array_dict_get_by('name', '.gitignore', config["children"])
        if config_gitignore is not None:
            # Use setdefault to initialize 'should_contain_lines' if not already present
            should_contain_lines = config_gitignore.setdefault("should_contain_lines", [])
            if isinstance(should_contain_lines, list):
                should_contain_lines.append("*.egg-info")
            else:
                raise ValueError("'should_contain_lines' must be a list")

        config["children"].append(
            {
                'name': 'pyproject.toml',
                'type': DiskItemType.FILE,
                'should_exist': True,
            }
        )

        return config
