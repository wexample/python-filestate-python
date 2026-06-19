from __future__ import annotations

import pytest


def test_toml_ensure_array_creates_when_missing() -> None:
    from wexample_filestate_python.helper.toml import toml_ensure_array

    tbl: dict = {}
    arr, changed = toml_ensure_array(tbl, "deps")
    assert changed is True
    assert "deps" in tbl


def test_toml_ensure_array_returns_existing_unchanged() -> None:
    from tomlkit import array

    from wexample_filestate_python.helper.toml import toml_ensure_array

    existing = array()
    tbl = {"deps": existing}
    arr, changed = toml_ensure_array(tbl, "deps")
    assert changed is False
    assert arr is existing


def test_toml_ensure_table_creates_nested_path() -> None:
    from tomlkit import document

    from wexample_filestate_python.helper.toml import toml_ensure_table

    doc = document()
    table, changed = toml_ensure_table(doc, ["tool", "pdm", "build"])
    assert changed is True
    assert "build" in doc["tool"]["pdm"]


def test_toml_ensure_table_existing_empty_path_unchanged() -> None:
    from tomlkit import document

    from wexample_filestate_python.helper.toml import toml_ensure_table

    doc = document()
    toml_ensure_table(doc, ["tool", "x"])
    _, changed = toml_ensure_table(doc, ["tool", "x"])
    assert changed is False


def test_toml_ensure_table_existing_non_empty_path_unchanged() -> None:
    from tomlkit import document

    from wexample_filestate_python.helper.toml import toml_ensure_table

    doc = document()
    toml_ensure_table(doc, ["tool", "x"])
    doc["tool"]["x"]["k"] = "v"
    _, changed = toml_ensure_table(doc, ["tool", "x"])
    assert changed is False


def test_toml_ensure_table_raises_on_empty_path() -> None:
    from tomlkit import document

    from wexample_filestate_python.helper.toml import toml_ensure_table

    with pytest.raises(ValueError, match=r"non-empty list"):
        toml_ensure_table(document(), [])


def test_toml_get_string_value_from_plain_value() -> None:
    from wexample_filestate_python.helper.toml import toml_get_string_value

    assert toml_get_string_value(42) == "42"


def test_toml_get_string_value_from_string_item() -> None:
    from tomlkit import item

    from wexample_filestate_python.helper.toml import toml_get_string_value

    assert toml_get_string_value(item("hello")) == "hello"


def test_toml_set_array_multiline_replaces_value() -> None:
    from tomlkit.items import Array

    from wexample_filestate_python.helper.toml import toml_set_array_multiline

    tbl: dict = {}
    arr = toml_set_array_multiline(tbl, "deps", ["a", "b"])
    assert isinstance(arr, Array)
    assert tbl["deps"] is arr
    assert list(arr) == ["a", "b"]


def test_toml_sort_string_array_already_sorted_returns_false() -> None:
    from tomlkit import array

    from wexample_filestate_python.helper.toml import toml_sort_string_array

    arr = array()
    arr.append("a")
    arr.append("b")
    assert toml_sort_string_array(arr) is False


def test_toml_sort_string_array_non_array_returns_false() -> None:
    from wexample_filestate_python.helper.toml import toml_sort_string_array

    assert toml_sort_string_array(["not", "an", "array"]) is False


def test_toml_sort_string_array_preserves_multiline_style() -> None:
    from tomlkit import array

    from wexample_filestate_python.helper.toml import toml_sort_string_array

    arr = array()
    arr.append("b")
    arr.append("a")
    arr.multiline(True)
    toml_sort_string_array(arr)
    assert "\n" in arr.as_string()


def test_toml_sort_string_array_preserves_single_line_style() -> None:
    from tomlkit import array

    from wexample_filestate_python.helper.toml import toml_sort_string_array

    arr = array()
    arr.append("b")
    arr.append("a")
    arr.multiline(False)
    toml_sort_string_array(arr)
    assert "\n" not in arr.as_string()


def test_toml_sort_string_array_sorts_case_insensitive() -> None:
    from tomlkit import array

    from wexample_filestate_python.helper.toml import toml_sort_string_array

    arr = array()
    arr.append("Banana")
    arr.append("apple")
    changed = toml_sort_string_array(arr)
    assert changed is True
    assert list(arr) == ["apple", "Banana"]
