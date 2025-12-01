from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_config.config_option.abstract_nested_config_option import (
    AbstractNestedConfigOption,
)
from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.option.mixin.option_mixin import OptionMixin
from wexample_helpers.decorator.base_class import base_class

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class PythonOption(OptionMixin, AbstractNestedConfigOption):
    @staticmethod
    def get_raw_value_allowed_type() -> Any:
        from wexample_filestate_python.config_value.python_config_value import (
            PythonConfigValue,
        )

        return Union[list[str], dict, PythonConfigValue]

    def create_required_operation(
        self, target: TargetFileOrDirectoryType, scopes: set[Scope]
    ) -> AbstractOperation | None:
        return self._create_child_required_operation(target=target, scopes=scopes)

    def get_allowed_options(self) -> list[type[AbstractConfigOption]]:
        # Import all the config options for each Python operation
        from wexample_filestate_python.option.python.add_future_annotations_option import (
            AddFutureAnnotationsOption,
        )
        from wexample_filestate_python.option.python.add_return_types_option import (
            AddReturnTypesOption,
        )
        from wexample_filestate_python.option.python.class_name_matches_file_name_option import (
            ClassNameMatchesFileNameOption,
        )
        from wexample_filestate_python.option.python.fix_attrs_option import (
            FixAttrsOption,
        )
        from wexample_filestate_python.option.python.fix_blank_lines_option import (
            FixBlankLinesOption,
        )
        from wexample_filestate_python.option.python.format_option import FormatOption
        from wexample_filestate_python.option.python.fstringify_option import (
            FstringifyOption,
        )
        from wexample_filestate_python.option.python.modernize_typing_option import (
            ModernizeTypingOption,
        )
        from wexample_filestate_python.option.python.order_class_attributes_option import (
            OrderClassAttributesOption,
        )
        from wexample_filestate_python.option.python.order_class_docstring_option import (
            OrderClassDocstringOption,
        )
        from wexample_filestate_python.option.python.order_class_methods_option import (
            OrderClassMethodsOption,
        )
        from wexample_filestate_python.option.python.order_constants_option import (
            OrderConstantsOption,
        )
        from wexample_filestate_python.option.python.order_iterable_items_option import (
            OrderIterableItemsOption,
        )
        from wexample_filestate_python.option.python.order_main_guard_option import (
            OrderMainGuardOption,
        )
        from wexample_filestate_python.option.python.order_module_docstring_option import (
            OrderModuleDocstringOption,
        )
        from wexample_filestate_python.option.python.order_module_functions_option import (
            OrderModuleFunctionsOption,
        )
        from wexample_filestate_python.option.python.order_module_metadata_option import (
            OrderModuleMetadataOption,
        )
        from wexample_filestate_python.option.python.order_type_checking_block_option import (
            OrderTypeCheckingBlockOption,
        )
        from wexample_filestate_python.option.python.relocate_imports_option import (
            RelocateImportsOption,
        )
        from wexample_filestate_python.option.python.remove_unused_option import (
            RemoveUnusedOption,
        )
        from wexample_filestate_python.option.python.sort_imports_option import (
            SortImportsOption,
        )
        from wexample_filestate_python.option.python.unquote_annotations_option import (
            UnquoteAnnotationsOption,
        )

        return [
            # filestate: python-iterable-sort
            AddFutureAnnotationsOption,
            AddReturnTypesOption,
            ClassNameMatchesFileNameOption,
            FixAttrsOption,
            FixBlankLinesOption,
            FormatOption,
            FstringifyOption,
            ModernizeTypingOption,
            OrderClassAttributesOption,
            OrderClassDocstringOption,
            OrderClassMethodsOption,
            OrderConstantsOption,
            OrderIterableItemsOption,
            OrderMainGuardOption,
            OrderModuleDocstringOption,
            OrderModuleFunctionsOption,
            OrderModuleMetadataOption,
            OrderTypeCheckingBlockOption,
            RelocateImportsOption,
            RemoveUnusedOption,
            SortImportsOption,
            UnquoteAnnotationsOption,
        ]

    def set_value(self, raw_value: Any) -> None:
        # Convert list form to dict form for consistency
        if isinstance(raw_value, list):
            dict_value = {}
            for option_name in raw_value:
                dict_value[option_name] = True
            raw_value = dict_value

        super().set_value(raw_value=raw_value)
