from typing import Any, List, ClassVar

from wexample_config.config_option.abstract_config_option import AbstractConfigOption


class PythonConfigOption(AbstractConfigOption):
    OPTION_NAME_FORMAT: ClassVar[str] = "format"
    OPTION_NAME_SORT_IMPORTS: ClassVar[str] = "sort_imports"

    @staticmethod
    def get_raw_value_allowed_type() -> Any:
        return List[str]
