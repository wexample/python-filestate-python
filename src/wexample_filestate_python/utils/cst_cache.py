"""Per-target libcst parse cache.

Within a single rectification scan, a Python file's disk content does not
change — yet historically each option parsed the libcst module independently,
multiplying the parse cost by the number of content options (~15). This
helper caches the `(src, module)` pair on the target item so all options on
the same file share a single parse.

The cache is naturally invalidated between rectification passes (a new
workdir means new target instances).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import libcst as cst

    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


_CACHE_ATTR = "_cst_cache"


def get_python_source_and_module(
    target: TargetFileOrDirectoryType,
) -> tuple[str, cst.Module]:
    cached = getattr(target, _CACHE_ATTR, None)
    if cached is not None:
        return cached

    import libcst as cst

    src = target.get_local_file().read()
    module = cst.parse_module(src)
    setattr(target, _CACHE_ATTR, (src, module))
    return src, module
