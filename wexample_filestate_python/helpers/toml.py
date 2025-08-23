from __future__ import annotations

from typing import Any
from tomlkit.items import Array, String


def toml_sort_string_array(arr: Any) -> bool:
    """
    Sort a tomlkit Array of String items in-place (case-insensitive) while
    preserving the existing multiline/style flags.

    Returns True if the array was changed.
    """
    # Validate array type
    if not isinstance(arr, Array):
        return False

    items = list(arr)
    if not items or not all(isinstance(i, String) for i in items):
        return False

    values = [i.value for i in items]
    sorted_items = [x for _, x in sorted(zip([v.lower() for v in values], items), key=lambda t: t[0])]

    if items == sorted_items:
        return False

    multiline_flag = getattr(arr, "multiline", None)
    # Clear and re-append to preserve tomlkit item identity
    while len(arr):
        arr.pop()
    for item in sorted_items:
        arr.append(item)
    if multiline_flag is not None:
        arr.multiline(multiline_flag)
    return True
