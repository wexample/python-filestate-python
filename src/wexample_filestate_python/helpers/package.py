from __future__ import annotations

import ast
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

    dependencies = {}

    # First pass: collect all local packages
    for package_dir in packages_root.iterdir():
        if not package_dir.is_dir():
            continue

        package_info = package_get_info(package_dir)
        if package_info:
            name, _ = package_info
            dependencies[name] = set()

    # Second pass: analyze dependencies
    for package_dir in packages_root.iterdir():
        if not package_dir.is_dir():
            continue

        package_info = package_get_info(package_dir)
        if package_info:
            name, deps = package_info
            if name in dependencies:
                # Only keep dependencies that are local packages
                dependencies[name] = {dep for dep in deps if dep in dependencies}

    return dependencies


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
    import re as _re

    # strip extras, versions, markers
    base = _re.split(r"[\s<>=!~;\[]", val, maxsplit=1)[0]
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
                if isinstance(kw.value, ast.Str):
                    result[kw.arg] = kw.value.s
                elif isinstance(kw.value, ast.List):
                    result[kw.arg] = [
                        elt.s for elt in kw.value.elts if isinstance(elt, ast.Str)
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
