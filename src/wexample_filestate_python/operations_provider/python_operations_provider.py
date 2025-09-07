from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.operations_provider.abstract_operations_provider import (
    AbstractOperationsProvider,
)

if TYPE_CHECKING:
    from wexample_filestate.operation.abstract_operation import AbstractOperation


class PythonOperationsProvider(AbstractOperationsProvider):
    @staticmethod
    def get_operations() -> list[type[AbstractOperation]]:
        from wexample_filestate_python.operation.python_add_future_annotations_operation import (
            PythonAddFutureAnnotationsOperation,
        )
        from wexample_filestate_python.operation.python_add_return_types_operation import (
            PythonAddReturnTypesOperation,
        )
        from wexample_filestate_python.operation.python_format_operation import (
            PythonFormatOperation,
        )
        from wexample_filestate_python.operation.python_fstringify_operation import (
            PythonFStringifyOperation,
        )
        from wexample_filestate_python.operation.python_modernize_typing_operation import (
            PythonModernizeTypingOperation,
        )
        from wexample_filestate_python.operation.python_relocate_imports_operation import (
            PythonRelocateImportsOperation,
        )
        from wexample_filestate_python.operation.python_remove_unused_imports_operation import (
            PythonRemoveUnusedOperation,
        )
        from wexample_filestate_python.operation.python_sort_imports_operation import (
            PythonSortImportsOperation,
        )
        from wexample_filestate_python.operation.python_unquote_annotations_operation import (
            PythonUnquoteAnnotationsOperation,
        )
        from wexample_filestate_python.operation.python_order_module_docstring_operation import (
            PythonOrderModuleDocstringOperation,
        )
        from wexample_filestate_python.operation.python_order_type_checking_block_operation import (
            PythonOrderTypeCheckingBlockOperation,
        )

        return [
            PythonFormatOperation,
            PythonSortImportsOperation,
            PythonAddReturnTypesOperation,
            PythonModernizeTypingOperation,
            PythonRelocateImportsOperation,
            PythonFStringifyOperation,
            PythonRemoveUnusedOperation,
            PythonAddFutureAnnotationsOperation,
            PythonUnquoteAnnotationsOperation,
            PythonOrderModuleDocstringOperation,
            PythonOrderTypeCheckingBlockOperation,
        ]
