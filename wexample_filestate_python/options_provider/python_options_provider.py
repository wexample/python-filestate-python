from typing import TYPE_CHECKING, List, Type

from wexample_config.options_provider.abstract_options_provider import (
    AbstractOptionsProvider,
)
from wexample_filestate_python.config_option.python_config_option import (
    PythonConfigOption,
)

if TYPE_CHECKING:
    from wexample_config.config_option.abstract_config_option import (
        AbstractConfigOption,
    )


class PythonOptionsProvider(AbstractOptionsProvider):
    @classmethod
    def get_options(cls) -> List[Type["AbstractConfigOption"]]:
        return [
            PythonConfigOption,
        ]
