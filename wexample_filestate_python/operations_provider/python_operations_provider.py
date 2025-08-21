from typing import TYPE_CHECKING, List, Type

from wexample_filestate.operations_provider.abstract_operations_provider import \
    AbstractOperationsProvider

if TYPE_CHECKING:
    from wexample_filestate.operation.abstract_operation import \
        AbstractOperation


class PythonOperationsProvider(AbstractOperationsProvider):
    @staticmethod
    def get_operations() -> List[Type["AbstractOperation"]]:
        from wexample_filestate_python.operation.python_format_operation import (
            PythonFormatOperation,
        )
        from wexample_filestate_python.operation.python_sort_imports_operation import (
            PythonSortImportsOperation,
        )
        from wexample_filestate_python.operation.python_add_return_types_operation import (
            PythonAddReturnTypesOperation,
        )

        return [
            PythonFormatOperation,
            PythonSortImportsOperation,
            PythonAddReturnTypesOperation,
        ]
