from __future__ import annotations

from pathlib import Path

import pytest

_PYPROJECT = """
[project]
name = "my-package"
dependencies = ["other-package", "external-lib>=1.0"]
"""

_SETUP_PY = """
from setuptools import setup

setup(
    name="legacy-package",
    install_requires=["dep-one", "dep-two"],
)
"""


def test_package_get_dependencies_keeps_only_local(tmp_path: Path) -> None:
    from wexample_filestate_python.helper.package import package_get_dependencies

    pkg_a = tmp_path / "a"
    pkg_b = tmp_path / "b"
    pkg_a.mkdir()
    pkg_b.mkdir()
    (pkg_a / "pyproject.toml").write_text(
        '[project]\nname = "a"\ndependencies = ["b", "external"]\n'
    )
    (pkg_b / "pyproject.toml").write_text('[project]\nname = "b"\ndependencies = []\n')

    result = package_get_dependencies(tmp_path)
    assert result == {"a": {"b"}, "b": set()}


def test_package_get_dependencies_raises_on_missing_dir(tmp_path: Path) -> None:
    from wexample_filestate_python.helper.package import package_get_dependencies

    with pytest.raises(ValueError, match=r"does not exist or is not a directory"):
        package_get_dependencies(tmp_path / "nope")


def test_package_get_info_prefers_pyproject(tmp_path: Path) -> None:
    from wexample_filestate_python.helper.package import package_get_info

    (tmp_path / "pyproject.toml").write_text(_PYPROJECT)
    name, deps = package_get_info(tmp_path)
    assert name == "my-package"
    assert deps == {"other-package", "external-lib>=1.0"}


def test_package_get_info_returns_none_without_metadata(tmp_path: Path) -> None:
    from wexample_filestate_python.helper.package import package_get_info

    assert package_get_info(tmp_path) is None


def test_package_normalize_name_strips_version_and_extras() -> None:
    from wexample_filestate_python.helper.package import package_normalize_name

    assert package_normalize_name("My-Package>=1.0") == "my-package"
    assert package_normalize_name("pkg[extra]") == "pkg"
    assert package_normalize_name("Foo;python_version<'3'") == "foo"


def test_package_parse_setup_extracts_name_and_deps(tmp_path: Path) -> None:
    from wexample_filestate_python.helper.package import package_parse_setup

    setup_path = tmp_path / "setup.py"
    setup_path.write_text(_SETUP_PY)
    metadata = package_parse_setup(setup_path)
    assert metadata["name"] == "legacy-package"
    assert metadata["install_requires"] == ["dep-one", "dep-two"]


def test_package_parse_toml_extracts_name_and_deps(tmp_path: Path) -> None:
    from wexample_filestate_python.helper.package import package_parse_toml

    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_text(_PYPROJECT)
    metadata = package_parse_toml(toml_path)
    assert metadata["name"] == "my-package"
    assert metadata["install_requires"] == ["other-package", "external-lib>=1.0"]


def test_package_parse_toml_returns_empty_on_invalid(tmp_path: Path) -> None:
    from wexample_filestate_python.helper.package import package_parse_toml

    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_text("not valid toml = =")
    assert package_parse_toml(toml_path) == {}
