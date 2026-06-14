from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

import tomli

if TYPE_CHECKING:
    from pathlib import Path


def package_get_dependencies(root_dir: str | Path) -> dict[str, set[str]]:
    """
    Get dependencies between packages in a directory.
    """
    from pathlib import Path

    packages_root = Path(root_dir)
    if not packages_root.exists() or not packages_root.is_dir():
        raise ValueError(f"Error: {packages_root} does not exist or is not a directory")

    # Filter to directories once; avoids repeated is_dir() calls in two passes.
    all_dirs = [e for e in packages_root.iterdir() if e.is_dir()]

    # Single pass: collect all local package infos (name → raw deps).
    pkg_infos: dict[str, set[str]] = {}
    for package_dir in all_dirs:
        package_info = package_get_info(package_dir)
        if package_info:
            name, deps = package_info
            pkg_infos[name] = deps

    local_names: set[str] = set(pkg_infos)  # O(1) membership for filtering

    # Keep only deps that resolve to a local package (set intersection).
    return {name: deps & local_names for name, deps in pkg_infos.items()}


def package_get_info(package_dir: Path) -> tuple[str, set[str]] | None:
    """
    Get package name and its dependencies from setup.py or pyproject.toml.
    """
    # Try pyproject.toml first
    toml_path = package_dir / "pyproject.toml"
    if toml_path.exists():
        metadata = package_parse_toml(toml_path)
    else:
        # Fallback to setup.py
        setup_py_path = package_dir / "setup.py"
        if setup_py_path.exists():
            metadata = package_parse_setup(setup_py_path)
        else:
            return None

    name = metadata.get("name")
    if not name:
        return None

    deps = metadata.get("install_requires", [])
    return name, set(deps)


def package_normalize_name(val: str) -> str:
    # strip extras, versions, markers
    base = re.split(r"[\s<>=!~;\[]", val, maxsplit=1)[0]
    return base.strip().lower()


def package_parse_setup(path: Path) -> dict:
    """
    Parse a setup.py file to extract metadata.
    """
    with open(path) as f:
        content = f.read()

    tree = ast.parse(content)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "setup"
        ):
            result = {}
            for kw in node.keywords:
                if isinstance(kw.value, ast.Constant) and isinstance(
                    kw.value.value, str
                ):
                    result[kw.arg] = kw.value.value
                elif isinstance(kw.value, ast.List):
                    result[kw.arg] = [
                        elt.value
                        for elt in kw.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    ]
            return result
    return {}


def package_parse_toml(path: Path) -> dict:
    """
    Parse a pyproject.toml file to extract metadata.
    """
    try:
        with open(path, "rb") as f:
            data = tomli.load(f)
            if "project" in data:
                project_data = data["project"]
                return {
                    "name": project_data.get("name"),
                    "install_requires": project_data.get("dependencies", []),
                }
    except Exception as e:
        print(f"Error parsing {path}: {e}")
    return {}
