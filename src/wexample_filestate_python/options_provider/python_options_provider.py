from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_config.options_provider.abstract_options_provider import (
    AbstractOptionsProvider,
)

if TYPE_CHECKING:
    from wexample_config.config_option.abstract_config_option import (
        AbstractConfigOption,
    )


class PythonOptionsProvider(AbstractOptionsProvider):
    # Do NOT cache the returned list in a `cls._options_cache` class attribute.
    # The cache is inherited via MRO, so a write from the base shadows what
    # subclasses should return. Roadmap the optim instead.
    @classmethod
    def get_options(cls) -> list[type[AbstractConfigOption]]:
        from wexample_filestate_python.option.python_option import (
            PythonOption,
        )

        return [
            PythonOption,
        ]
