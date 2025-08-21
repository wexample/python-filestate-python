from typing import TYPE_CHECKING, List, Type

from wexample_filestate.operation.content_trim_operation import ContentTrimOperation
from wexample_filestate.operations_provider.abstract_operations_provider import (
    AbstractOperationsProvider,
)

if TYPE_CHECKING:
    from wexample_filestate.operation.abstract_operation import AbstractOperation


class PythonOperationsProvider(AbstractOperationsProvider):
    @staticmethod
    def get_operations() -> List[Type["AbstractOperation"]]:
        from wexample_filestate_python.operation.python_format_operation import PythonFormatOperation

        return [
            PythonFormatOperation,
        ]
