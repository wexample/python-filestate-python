from __future__ import annotations

import libcst as cst


# Collect existing from-imports into a map: imported_name -> (module, alias)
# Only handle `from pkg import Name [as Alias]`. Skip star imports and bare `import pkg`.
class PythonParserImportIndex(cst.CSTVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.name_to_from: dict[str, tuple[str | None, str | None]] = {}
        self.importfrom_nodes: list[cst.ImportFrom] = []
        self.other_import_nodes: list[cst.Import] = []

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:  # type: ignore[override]
        self.importfrom_nodes.append(node)
        if node.names is None or isinstance(node.names, cst.ImportStar):
            return
        module_name = None
        if node.module is not None:
            if isinstance(node.module, cst.Name):
                module_name = node.module.value
            elif isinstance(node.module, cst.Attribute):
                module_name = (
                    node.module.attr.value
                    if isinstance(node.module.attr, cst.Name)
                    else None
                )
            elif isinstance(node.module, cst.SimpleString):
                module_name = node.module.evaluated_value  # unlikely
        for alias in node.names:
            if isinstance(alias, cst.ImportAlias):
                asname = alias.asname.name.value if alias.asname else None
                name = alias.name.value if isinstance(alias.name, cst.Name) else None
                if name:
                    self.name_to_from[name if not asname else asname] = (
                        module_name,
                        asname,
                    )

    def visit_Import(self, node: cst.Import) -> None:  # type: ignore[override]
        self.other_import_nodes.append(node)
