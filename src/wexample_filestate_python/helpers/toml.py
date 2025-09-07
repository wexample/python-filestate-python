from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tomlkit.items import Array


def toml_ensure_array(tbl: Any, key: str) -> tuple[Any, bool]:
    """
    Ensure an array exists at tbl[key] and return (array, changed).
    Uses tomlkit.array() for creation.
    """
    from tomlkit import array

    arr = tbl.get(key) if isinstance(tbl, dict) else None
    if arr is None:
        arr = array()
        tbl[key] = arr
        return arr, True
    return arr, False


def toml_ensure_array_multiline(tbl: Any, key: str) -> tuple[Array, bool]:
    """
    Ensure an array exists at tbl[key] and force multiline formatting.
    Returns (array, changed_created).
    """
    from tomlkit.items import Array

    arr, changed = toml_ensure_array(tbl, key)
    # Force multiline for readability when dumping
    if isinstance(arr, Array):
        arr.multiline(True)
    return arr, changed


def toml_ensure_table(doc: Any, path: list[str]) -> tuple[Any, bool]:
    """
    Ensure a nested TOML table exists and return (table, changed).
    Path example: ["tool", "pdm", "build"]. Uses tomlkit.table() for missing parts.
    """
    from tomlkit import table

    if not isinstance(path, list) or not path:
        raise ValueError("path must be a non-empty list of keys")

    changed = False
    current = doc
    for key in path:
        tbl = current.get(key) if isinstance(current, dict) else None
        if not tbl or not isinstance(tbl, dict):
            tbl = table()
            current[key] = tbl
            changed = True
        current = tbl
    return current, changed


def toml_get_string_value(item: Any) -> str:
    """Return the string content of a tomlkit String or generic item as str."""
    from tomlkit.items import String

    if isinstance(item, String):
        return item.value
    return str(item)


def toml_set_array_multiline(tbl: Any, key: str, values: list[Any]) -> Array:
    """
    Replace tbl[key] with a tomlkit array built from values and set multiline(True).
    Returns the created Array instance.
    """
    from tomlkit import array

    arr = array(values)
    arr.multiline(True)
    tbl[key] = arr
    return arr


def toml_sort_string_array(arr: Any) -> bool:
    """
    Sort a tomlkit Array of String items in-place (case-insensitive) while
    preserving the existing multiline/style flags.

    Returns True if the array was changed.
    """
    from tomlkit.items import Array, String

    # Validate array type
    if not isinstance(arr, Array):
        return False

    items = list(arr)
    if not items or not all(isinstance(i, String) for i in items):
        return False

    values = [i.value for i in items]
    sorted_items = [
        x
        for _, x in sorted(zip([v.lower() for v in values], items), key=lambda t: t[0])
    ]

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
