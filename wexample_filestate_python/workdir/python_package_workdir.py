from typing import Optional

from wexample_filestate_python.workdir.python_workdir import PythonWorkdir
from wexample_config.const.types import DictConfig


class PythonPackageWorkdir(PythonWorkdir):
    def prepare_value(self, config: Optional[DictConfig] = None) -> DictConfig:
        from wexample_filestate.const.disk import DiskItemType

        config = super().prepare_value(config)

        config.update({
            "children": [
                {
                    'name': 'pyproject.toml',
                    'type': DiskItemType.FILE,
                    'should_exist': True,
                },
            ]
        })

        return config
