from typing import Any, ClassVar, List

from wexample_config.config_option.abstract_config_option import AbstractConfigOption


class PythonConfigOption(AbstractConfigOption):
    OPTION_NAME_FORMAT: ClassVar[str] = "format"
    OPTION_NAME_SORT_IMPORTS: ClassVar[str] = "sort_imports"
    OPTION_NAME_ADD_RETURN_TYPES: ClassVar[str] = "add_return_types"
    OPTION_NAME_MODERNIZE_TYPING: ClassVar[str] = "modernize_typing"
    OPTION_NAME_FSTRINGIFY: ClassVar[str] = "fstringify"

    @staticmethod
    def get_raw_value_allowed_type() -> Any:
        return list[str]
