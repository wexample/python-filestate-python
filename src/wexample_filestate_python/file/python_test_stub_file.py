from __future__ import annotations

from wexample_helpers.decorator.base_class import base_class

from wexample_filestate_python.file.python_file import PythonFile


@base_class
class PythonTestStubFile(PythonFile):
    """A pytest stub generated as a sidecar of a Python module.

    When used in a `sidecar_of` declaration as the `cls`, this class is
    instantiated for each missing test file the framework needs to create.
    `build_default_content()` is the hook `SidecarOfOption` wires into the
    standard `default_content` flow — it reads the primary module via the
    shared `cst_cache`, enumerates its public top-level functions and the
    public methods of each top-level class, and emits a minimal pytest
    skeleton (one `test_*` per public callable, wrapped in a
    `TestPascalCase` class when the primary has classes).

    Intentionally minimal:
      - Generates `pass` bodies so the human fills them in.
      - Skips private callables (`_*`) and dunders.
      - Skips classes that look abstract (decorated `@abstract_class` or
        prefixed `Abstract`) — they don't need direct tests.
    """

    def build_default_content(self) -> str:
        primary = self.get_sidecar_primary()
        primary_path = primary.get_path()

        from wexample_filestate_python.utils.cst_cache import (
            get_python_source_and_module,
        )

        _, module = get_python_source_and_module(primary)
        return _render_stub(
            primary_module_name=primary_path.stem,
            module=module,
        )


def _render_stub(primary_module_name: str, module) -> str:
    import libcst as cst

    lines: list[str] = [
        "from __future__ import annotations",
        "",
    ]

    classes_emitted = False
    for node in module.body:
        if isinstance(node, cst.ClassDef):
            class_name = node.name.value
            if _is_skippable_class(class_name, node):
                continue
            methods = _public_method_names(node)
            if not methods:
                continue
            lines.append(f"class Test{class_name}:")
            for method_name in methods:
                lines.extend([
                    f"    def test_{method_name}(self) -> None:",
                    "        pass",
                    "",
                ])
            classes_emitted = True

    func_names = _public_function_names(module)
    if func_names:
        if classes_emitted:
            lines.append("")
        for func_name in func_names:
            lines.extend([
                f"def test_{func_name}() -> None:",
                "    pass",
                "",
            ])

    if not classes_emitted and not func_names:
        # No public surface — emit a placeholder so the file is valid pytest
        # and the human knows the stub generator ran but found nothing.
        lines.append(f"# Auto-generated stub for {primary_module_name}.py.")
        lines.append(
            "# No public functions/classes detected — add tests manually."
        )
        lines.append("")

    return "\n".join(lines)


def _public_function_names(module) -> list[str]:
    import libcst as cst

    return [
        node.name.value
        for node in module.body
        if isinstance(node, cst.FunctionDef) and not node.name.value.startswith("_")
    ]


def _public_method_names(class_node) -> list[str]:
    import libcst as cst

    statements = getattr(class_node.body, "body", ())
    return [
        stmt.name.value
        for stmt in statements
        if isinstance(stmt, cst.FunctionDef) and not stmt.name.value.startswith("_")
    ]


def _is_skippable_class(class_name: str, class_node) -> bool:
    import libcst as cst

    if class_name.startswith("Abstract"):
        return True
    for decorator in class_node.decorators:
        expr = decorator.decorator
        if isinstance(expr, cst.Name) and expr.value in (
            "abstract_class",
            "abstractmethod",
        ):
            return True
        if isinstance(expr, cst.Call) and isinstance(expr.func, cst.Name):
            if expr.func.value == "abstract_class":
                return True
    return False
