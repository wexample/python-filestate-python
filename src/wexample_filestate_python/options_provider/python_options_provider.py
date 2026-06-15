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
    @classmethod
    def get_options(cls) -> list[type[AbstractConfigOption]]:
        # Use `cls.__dict__` (not `hasattr`) so each class in the hierarchy
        # maintains its own cache without the MRO inheritance side-effect.
        if "_options_cache" not in cls.__dict__:
            from wexample_filestate_python.option.python_option import (
                PythonOption,
            )

            cls._options_cache: list[type[AbstractConfigOption]] = [PythonOption]
        return cls._options_cache
