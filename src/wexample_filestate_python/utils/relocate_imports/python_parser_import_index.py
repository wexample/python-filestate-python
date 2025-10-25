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

    @staticmethod
    def _flatten_module_name(module: cst.BaseExpression | None) -> str | None:
        if module is None:
            return None
        if isinstance(module, cst.Name):
            return module.value
        if isinstance(module, cst.Attribute):
            parts: list[str] = []
            cur: cst.BaseExpression | None = module
            while isinstance(cur, cst.Attribute):
                if isinstance(cur.attr, cst.Name):
                    parts.append(cur.attr.value)
                else:
                    break
                cur = cur.value
            if isinstance(cur, cst.Name):
                parts.append(cur.value)
            parts.reverse()
            return ".".join(parts) if parts else None
        if isinstance(module, cst.SimpleString):
            return module.evaluated_value
        return None

    def visit_Import(self, node: cst.Import) -> None:  # type: ignore[override]
        self.other_import_nodes.append(node)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:  # type: ignore[override]
        module_name = self._flatten_module_name(node.module)
        
        # Skip __future__ imports - they must always stay at module top
        if module_name == "__future__":
            return
            
        self.importfrom_nodes.append(node)
        if node.names is None or isinstance(node.names, cst.ImportStar):
            return
        for alias in node.names:
            if isinstance(alias, cst.ImportAlias):
                asname = alias.asname.name.value if alias.asname else None
                name = alias.name.value if isinstance(alias.name, cst.Name) else None
                if name:
                    self.name_to_from[name if not asname else asname] = (
                        module_name,
                        asname,
                    )
