import ast
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple

import tomli


def package_parse_setup(path: Path) -> Dict:
    """
    Parse a setup.py file to extract metadata.
    """
    with open(path) as f:
        content = f.read()

    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'setup':
            result = {}
            for kw in node.keywords:
                if isinstance(kw.value, ast.Str):
                    result[kw.arg] = kw.value.s
                elif isinstance(kw.value, ast.List):
                    result[kw.arg] = [
                        elt.s for elt in kw.value.elts
                        if isinstance(elt, ast.Str)
                    ]
            return result
    return {}


def package_parse_toml(path: Path) -> Dict:
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
                    "install_requires": project_data.get("dependencies", [])
                }
    except Exception as e:
        print(f"Error parsing {path}: {e}")
    return {}


def package_get_info(package_dir: Path) -> Optional[Tuple[str, Set[str]]]:
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


def package_get_dependencies(root_dir: str | Path) -> Dict[str, Set[str]]:
    """
    Get dependencies between packages in a directory.
    """
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
                dependencies[name] = {
                    dep for dep in deps
                    if dep in dependencies
                }

    return dependencies


def package_list_sorted(root_dir: str | Path) -> List[str]:
    """
    Get a list of package names sorted by dependency order.
    """
    from wexample_filestate_dev.helpers.dependencies import dependencies_sort

    dependencies = package_get_dependencies(root_dir)
    if not dependencies:
        return []

    # Convert dependencies dict to list for sorting
    packages = list(dependencies.keys())

    def get_deps(pkg: str) -> Set[str]:
        return dependencies[pkg]

    return dependencies_sort(packages, get_deps)
