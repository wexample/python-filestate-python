from typing import Any, ClassVar, Union, TYPE_CHECKING

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_config.config_option.abstract_nested_config_option import AbstractNestedConfigOption
from wexample_filestate.option.mixin.option_mixin import OptionMixin
from wexample_helpers.decorator.base_class import base_class

if TYPE_CHECKING:
    from wexample_filestate.operation.abstract_operation import AbstractOperation
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class PythonOption(OptionMixin, AbstractNestedConfigOption):
    # filestate: python-constant-sort
    # New preferred option name to add `from __future__ import annotations`
    OPTION_NAME_ADD_FUTURE_ANNOTATIONS: ClassVar[str] = "add_future_annotations"
    OPTION_NAME_ADD_RETURN_TYPES: ClassVar[str] = "add_return_types"
    # Fix attrs usage (ensure kw_only=True, etc.)
    OPTION_NAME_FIX_ATTRS: ClassVar[str] = "fix_attrs"
    # Fix blank lines in Python files (after signatures, docstrings, etc.)
    OPTION_NAME_FIX_BLANK_LINES: ClassVar[str] = "fix_blank_lines"
    OPTION_NAME_FORMAT: ClassVar[str] = "format"
    OPTION_NAME_FSTRINGIFY: ClassVar[str] = "fstringify"
    OPTION_NAME_MODERNIZE_TYPING: ClassVar[str] = "modernize_typing"
    # Sort class attributes: special first, then public A–Z, then private/protected A–Z
    OPTION_NAME_ORDER_CLASS_ATTRIBUTES: ClassVar[str] = "order_class_attributes"
    # Ensure class docstring is first statement after header/decorators
    OPTION_NAME_ORDER_CLASS_DOCSTRING: ClassVar[str] = "order_class_docstring"
    # Order class methods (dunders sequence, class/staticmethods, properties, instances)
    OPTION_NAME_ORDER_CLASS_METHODS: ClassVar[str] = "order_class_methods"
    # Sort flagged UPPER_CASE constant blocks at module level
    OPTION_NAME_ORDER_CONSTANTS: ClassVar[str] = "order_constants"
    # Sort items inside flagged iterable literals (lists/dicts)
    OPTION_NAME_ORDER_ITERABLE_ITEMS: ClassVar[str] = "order_iterable_items"
    # Ensure if __name__ == "__main__" block is at the very end
    OPTION_NAME_ORDER_MAIN_GUARD: ClassVar[str] = "order_main_guard"
    # Order module docstring to be at the top of the file
    OPTION_NAME_ORDER_MODULE_DOCSTRING: ClassVar[str] = "order_module_docstring"
    # Order module-level functions (public A–Z, then private)
    OPTION_NAME_ORDER_MODULE_FUNCTIONS: ClassVar[str] = "order_module_functions"
    # Group and sort module metadata at module level
    OPTION_NAME_ORDER_MODULE_METADATA: ClassVar[str] = "order_module_metadata"
    # Normalize blank lines between program structures (spacing rules)
    OPTION_NAME_ORDER_SPACING: ClassVar[str] = "order_spacing"
    # Move TYPE_CHECKING blocks to after regular imports
    OPTION_NAME_ORDER_TYPE_CHECKING_BLOCK: ClassVar[str] = "order_type_checking_block"
    # Relocate imports by usage (runtime-in-method, class property types, type-only)
    OPTION_NAME_RELOCATE_IMPORTS: ClassVar[str] = "relocate_imports"
    OPTION_NAME_REMOVE_UNUSED: ClassVar[str] = "remove_unused"
    OPTION_NAME_SORT_IMPORTS: ClassVar[str] = "sort_imports"
    # New policy: unquote annotations (remove string annotations)
    OPTION_NAME_UNQUOTE_ANNOTATIONS: ClassVar[str] = "unquote_annotations"

    @staticmethod
    def get_raw_value_allowed_type() -> Any:
        from wexample_filestate_python.config_value.python_config_value import PythonConfigValue
        
        return Union[list[str], dict, PythonConfigValue]

    def set_value(self, raw_value: Any) -> None:
        # Convert list form to dict form for consistency
        if isinstance(raw_value, list):
            dict_value = {}
            for option_name in raw_value:
                dict_value[option_name] = True
            raw_value = dict_value
        
        super().set_value(raw_value=raw_value)

    def get_allowed_options(self) -> list[type[AbstractConfigOption]]:
        # Import all the config options for each Python operation
        from wexample_filestate_python.option.add_future_annotations_option import AddFutureAnnotationsConfigOption
        from wexample_filestate_python.option.add_return_types_option import AddReturnTypesConfigOption
        from wexample_filestate_python.option.fix_attrs_option import FixAttrsConfigOption
        from wexample_filestate_python.option.fix_blank_lines_option import FixBlankLinesConfigOption
        from wexample_filestate_python.option.format_option import FormatConfigOption
        from wexample_filestate_python.option.fstringify_option import FstringifyConfigOption
        from wexample_filestate_python.option.modernize_typing_option import ModernizeTypingConfigOption
        from wexample_filestate_python.option.order_class_attributes_option import OrderClassAttributesConfigOption
        from wexample_filestate_python.option.order_class_docstring_option import OrderClassDocstringConfigOption
        from wexample_filestate_python.option.order_class_methods_option import OrderClassMethodsConfigOption
        from wexample_filestate_python.option.order_constants_option import OrderConstantsConfigOption
        from wexample_filestate_python.option.order_iterable_items_option import OrderIterableItemsConfigOption
        from wexample_filestate_python.option.order_main_guard_option import OrderMainGuardConfigOption
        from wexample_filestate_python.option.order_module_docstring_option import OrderModuleDocstringConfigOption
        from wexample_filestate_python.option.order_module_functions_option import OrderModuleFunctionsConfigOption
        from wexample_filestate_python.option.order_module_metadata_option import OrderModuleMetadataConfigOption
        from wexample_filestate_python.option.order_type_checking_block_option import OrderTypeCheckingBlockConfigOption
        from wexample_filestate_python.option.relocate_imports_option import RelocateImportsConfigOption
        from wexample_filestate_python.option.remove_unused_option import RemoveUnusedConfigOption
        from wexample_filestate_python.option.sort_imports_option import SortImportsConfigOption
        from wexample_filestate_python.option.unquote_annotations_option import UnquoteAnnotationsConfigOption

        return [
            AddFutureAnnotationsConfigOption,
            AddReturnTypesConfigOption,
            FixAttrsConfigOption,
            FixBlankLinesConfigOption,
            FormatConfigOption,
            FstringifyConfigOption,
            ModernizeTypingConfigOption,
            OrderClassAttributesConfigOption,
            OrderClassDocstringConfigOption,
            OrderClassMethodsConfigOption,
            OrderConstantsConfigOption,
            OrderIterableItemsConfigOption,
            OrderMainGuardConfigOption,
            OrderModuleDocstringConfigOption,
            OrderModuleFunctionsConfigOption,
            OrderModuleMetadataConfigOption,
            OrderTypeCheckingBlockConfigOption,
            RelocateImportsConfigOption,
            RemoveUnusedConfigOption,
            SortImportsConfigOption,
            UnquoteAnnotationsConfigOption,
        ]

    def create_required_operation(self, target: "TargetFileOrDirectoryType") -> "AbstractOperation | None":
        """Create operation by iterating through all enabled sub-options."""
        for option_class in self.get_allowed_options():
            option = self.get_option_value(option_class)
            if option and hasattr(option, 'create_required_operation'):
                operation = option.create_required_operation(target)
                if operation:
                    # Return the first operation found
                    return operation
        
        return None

    def _read_current_content(self, target: "TargetFileOrDirectoryType") -> str | None:
        """Read current file content, return None if file doesn't exist."""
        if not target.source or not target.source.get_path().exists():
            return None
        return target.get_local_file().read()

    def _create_file_write_operation(self, **kwargs):
        from wexample_filestate.operation.file_write_operation import FileWriteOperation
        
        return FileWriteOperation(**kwargs)
