from __future__ import annotations

from typing import Any

from wexample_config.config_value.config_value import ConfigValue
from wexample_helpers.classes.field import public_field
from wexample_helpers.decorator.base_class import base_class


@base_class
class PythonConfigValue(ConfigValue):
    add_future_annotations: bool | None = public_field(
        default=None,
        description="Add `from __future__ import annotations`",
    )
    add_return_types: bool | None = public_field(
        default=None,
        description="Add return type annotations",
    )
    fix_attrs: bool | None = public_field(
        default=None,
        description="Fix attrs usage (ensure kw_only=True, etc.)",
    )
    fix_blank_lines: bool | None = public_field(
        default=None,
        description="Fix blank lines in Python files",
    )
    format: bool | None = public_field(
        default=None,
        description="Format Python code",
    )
    fstringify: bool | None = public_field(
        default=None,
        description="Convert string formatting to f-strings",
    )
    modernize_typing: bool | None = public_field(
        default=None,
        description="Modernize typing annotations",
    )
    order_class_attributes: bool | None = public_field(
        default=None,
        description="Sort class attributes: special first, then public A–Z, then private/protected A–Z",
    )
    order_class_docstring: bool | None = public_field(
        default=None,
        description="Ensure class docstring is first statement after header/decorators",
    )
    order_class_methods: bool | None = public_field(
        default=None,
        description="Order class methods (dunders sequence, class/staticmethods, properties, instances)",
    )
    order_constants: bool | None = public_field(
        default=None,
        description="Sort flagged UPPER_CASE constant blocks at module level",
    )
    order_iterable_items: bool | None = public_field(
        default=None,
        description="Sort items inside flagged iterable literals (lists/dicts)",
    )
    order_main_guard: bool | None = public_field(
        default=None,
        description="Ensure if __name__ == '__main__' block is at the very end",
    )
    order_module_docstring: bool | None = public_field(
        default=None,
        description="Order module docstring to be at the top of the file",
    )
    order_module_functions: bool | None = public_field(
        default=None,
        description="Order module-level functions (public A–Z, then private)",
    )
    order_module_metadata: bool | None = public_field(
        default=None,
        description="Group and sort module metadata at module level",
    )
    order_spacing: bool | None = public_field(
        default=None,
        description="Normalize blank lines between program structures (spacing rules)",
    )
    order_type_checking_block: bool | None = public_field(
        default=None,
        description="Move TYPE_CHECKING blocks to after regular imports",
    )
    raw: Any = public_field(
        default=None, description="Disabled raw value for this config."
    )
    relocate_imports: bool | None = public_field(
        default=None,
        description="Relocate imports by usage (runtime-in-method, class property types, type-only)",
    )
    remove_unused: bool | None = public_field(
        default=None,
        description="Remove unused imports",
    )
    sort_imports: bool | None = public_field(
        default=None,
        description="Sort imports",
    )
    unquote_annotations: bool | None = public_field(
        default=None,
        description="Unquote annotations (remove string annotations)",
    )

    def to_option_raw_value(self) -> Any:
        from wexample_filestate_python.config_option.add_future_annotations_config_option import (
            AddFutureAnnotationsConfigOption,
        )
        from wexample_filestate_python.config_option.add_return_types_config_option import (
            AddReturnTypesConfigOption,
        )
        from wexample_filestate_python.config_option.fix_attrs_config_option import (
            FixAttrsConfigOption,
        )
        from wexample_filestate_python.config_option.fix_blank_lines_config_option import (
            FixBlankLinesConfigOption,
        )
        from wexample_filestate_python.config_option.format_config_option import (
            FormatConfigOption,
        )
        from wexample_filestate_python.config_option.fstringify_config_option import (
            FstringifyConfigOption,
        )
        from wexample_filestate_python.config_option.modernize_typing_config_option import (
            ModernizeTypingConfigOption,
        )
        from wexample_filestate_python.config_option.order_class_attributes_config_option import (
            OrderClassAttributesConfigOption,
        )
        from wexample_filestate_python.config_option.order_class_docstring_config_option import (
            OrderClassDocstringConfigOption,
        )
        from wexample_filestate_python.config_option.order_class_methods_config_option import (
            OrderClassMethodsConfigOption,
        )
        from wexample_filestate_python.config_option.order_constants_config_option import (
            OrderConstantsConfigOption,
        )
        from wexample_filestate_python.config_option.order_iterable_items_config_option import (
            OrderIterableItemsConfigOption,
        )
        from wexample_filestate_python.config_option.order_main_guard_config_option import (
            OrderMainGuardConfigOption,
        )
        from wexample_filestate_python.config_option.order_module_docstring_config_option import (
            OrderModuleDocstringConfigOption,
        )
        from wexample_filestate_python.config_option.order_module_functions_config_option import (
            OrderModuleFunctionsConfigOption,
        )
        from wexample_filestate_python.config_option.order_module_metadata_config_option import (
            OrderModuleMetadataConfigOption,
        )
        from wexample_filestate_python.config_option.order_spacing_config_option import (
            OrderSpacingConfigOption,
        )
        from wexample_filestate_python.config_option.order_type_checking_block_config_option import (
            OrderTypeCheckingBlockConfigOption,
        )
        from wexample_filestate_python.config_option.relocate_imports_config_option import (
            RelocateImportsConfigOption,
        )
        from wexample_filestate_python.config_option.remove_unused_config_option import (
            RemoveUnusedConfigOption,
        )
        from wexample_filestate_python.config_option.sort_imports_config_option import (
            SortImportsConfigOption,
        )
        from wexample_filestate_python.config_option.unquote_annotations_config_option import (
            UnquoteAnnotationsConfigOption,
        )

        return {
            AddFutureAnnotationsConfigOption.get_name(): self.add_future_annotations,
            AddReturnTypesConfigOption.get_name(): self.add_return_types,
            FixAttrsConfigOption.get_name(): self.fix_attrs,
            FixBlankLinesConfigOption.get_name(): self.fix_blank_lines,
            FormatConfigOption.get_name(): self.format,
            FstringifyConfigOption.get_name(): self.fstringify,
            ModernizeTypingConfigOption.get_name(): self.modernize_typing,
            OrderClassAttributesConfigOption.get_name(): self.order_class_attributes,
            OrderClassDocstringConfigOption.get_name(): self.order_class_docstring,
            OrderClassMethodsConfigOption.get_name(): self.order_class_methods,
            OrderConstantsConfigOption.get_name(): self.order_constants,
            OrderIterableItemsConfigOption.get_name(): self.order_iterable_items,
            OrderMainGuardConfigOption.get_name(): self.order_main_guard,
            OrderModuleDocstringConfigOption.get_name(): self.order_module_docstring,
            OrderModuleFunctionsConfigOption.get_name(): self.order_module_functions,
            OrderModuleMetadataConfigOption.get_name(): self.order_module_metadata,
            OrderSpacingConfigOption.get_name(): self.order_spacing,
            OrderTypeCheckingBlockConfigOption.get_name(): self.order_type_checking_block,
            RelocateImportsConfigOption.get_name(): self.relocate_imports,
            RemoveUnusedConfigOption.get_name(): self.remove_unused,
            SortImportsConfigOption.get_name(): self.sort_imports,
            UnquoteAnnotationsConfigOption.get_name(): self.unquote_annotations,
        }
