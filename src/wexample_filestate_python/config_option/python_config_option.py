from typing import Any, ClassVar

from wexample_config.config_option.abstract_config_option import AbstractConfigOption


class PythonConfigOption(AbstractConfigOption):
    OPTION_NAME_FORMAT: ClassVar[str] = "format"
    OPTION_NAME_SORT_IMPORTS: ClassVar[str] = "sort_imports"
    OPTION_NAME_ADD_RETURN_TYPES: ClassVar[str] = "add_return_types"
    OPTION_NAME_MODERNIZE_TYPING: ClassVar[str] = "modernize_typing"
    OPTION_NAME_FSTRINGIFY: ClassVar[str] = "fstringify"
    OPTION_NAME_REMOVE_UNUSED: ClassVar[str] = "remove_unused"
    # New preferred option name to add `from __future__ import annotations`
    OPTION_NAME_ADD_FUTURE_ANNOTATIONS: ClassVar[str] = "add_future_annotations"
    # New policy: unquote annotations (remove string annotations)
    OPTION_NAME_UNQUOTE_ANNOTATIONS: ClassVar[str] = "unquote_annotations"
    # Relocate imports by usage (runtime-in-method, class property types, type-only)
    OPTION_NAME_RELOCATE_IMPORTS: ClassVar[str] = "relocate_imports"
    # Order module docstring to be at the top of the file
    OPTION_NAME_ORDER_MODULE_DOCSTRING: ClassVar[str] = "order_module_docstring"
    # Move TYPE_CHECKING blocks to after regular imports
    OPTION_NAME_ORDER_TYPE_CHECKING_BLOCK: ClassVar[str] = "order_type_checking_block"
    # Group and sort module metadata at module level
    OPTION_NAME_ORDER_MODULE_METADATA: ClassVar[str] = "order_module_metadata"
    # Sort flagged UPPER_CASE constant blocks at module level
    OPTION_NAME_ORDER_CONSTANTS: ClassVar[str] = "order_constants"
    # Sort items inside flagged iterable literals (lists/dicts)
    OPTION_NAME_ORDER_ITERABLE_ITEMS: ClassVar[str] = "order_iterable_items"

    @staticmethod
    def get_raw_value_allowed_type() -> Any:
        return list[str]
