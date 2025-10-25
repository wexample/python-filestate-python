from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class AddReturnTypesOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Add simple return type annotations (None/bool/str/int/float) when trivially inferable."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Add return type annotations for functions lacking them when trivially inferable.

        Phase 1: annotate -> None, -> bool, -> str, -> int, -> float when all return
        statements in a function agree on one of these literal types."""
        import libcst as cst

        src = target.get_local_file().read()

        # We implement type inference and rewriting using LibCST to ensure
        # robust, formatting-preserving edits. We extend inference to:
        # - simple literals (None, bool, str, int, float)
        # - simple class instantiation returns (MyClass() or via a variable assigned once)
        def _infer_literal_type(expr: cst.BaseExpression) -> str | None:
            if isinstance(expr, cst.Name):
                if expr.value in ("True", "False"):
                    return "bool"
                if expr.value == "None":
                    return "None"
                return None
            if isinstance(expr, cst.SimpleString):
                return "str"
            if isinstance(expr, cst.Integer):
                return "int"
            if isinstance(expr, cst.Float):
                return "float"
            return None

        class _ReturnCollector(cst.CSTVisitor):
            def __init__(self) -> None:
                self.returns: list[cst.Return] = []

            # Do not descend into nested scopes that could have their own returns
            def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # type: ignore[override]
                return False

            def visit_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> bool:  # type: ignore[override]
                return False

            def visit_Lambda(self, node: cst.Lambda) -> bool:  # type: ignore[override]
                return False

            def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # type: ignore[override]
                return False

            def visit_Return(self, node: cst.Return) -> None:  # type: ignore[override]
                self.returns.append(node)

        class _KnownTypesCollector(cst.CSTVisitor):
            """Collect known simple type names from class defs and from-imports.

            We stay conservative: only names directly available in the module namespace
            (class definitions and `from x import Name [as Alias]`).
            """

            def __init__(self) -> None:
                self.known: set[str] = set()

            def visit_ClassDef(self, node: cst.ClassDef) -> None:  # type: ignore[override]
                # Record class name as a potential return type
                self.known.add(node.name.value)

            def visit_ImportFrom(self, node: cst.ImportFrom) -> None:  # type: ignore[override]
                # from pkg import A as B -> record B (or A if no alias)
                for n in node.names:
                    if isinstance(n, cst.ImportAlias):
                        asname = n.asname.name.value if n.asname else None
                        name = n.name.value if isinstance(n.name, cst.Name) else None
                        if name:
                            self.known.add(asname or name)

        class _FunctionAssignCollector(cst.CSTVisitor):
            """Collect simple var -> class-call assignments in a function body.

            Only records the first simple assignment `x = MyClass(...)` where x is a Name
            and call target resolves to a known type. If a variable is assigned multiple
            times to different types, it is discarded.
            """

            def __init__(self, known_types: set[str]) -> None:
                self.known_types = known_types
                self.var_type: dict[str, str] = {}
                self.discarded: set[str] = set()

            def _infer_call_type(self, call: cst.Call) -> str | None:
                func = call.func
                if isinstance(func, cst.Name):
                    # Only keep conservative matches: known type names
                    if func.value in self.known_types and func.value[:1].isupper():
                        return func.value
                elif isinstance(func, cst.Attribute):
                    # module.MyClass(...) -> infer MyClass if it's a known type
                    if isinstance(func.attr, cst.Name):
                        attr_name = func.attr.value
                        if attr_name in self.known_types and attr_name[:1].isupper():
                            return attr_name
                return None

            def _record_assignment(
                self, target: cst.BaseExpression, value: cst.BaseExpression
            ) -> None:
                if not isinstance(target, cst.Name):
                    return
                var = target.value
                if var in self.discarded:
                    return
                if not isinstance(value, cst.Call):
                    return
                rtype = self._infer_call_type(value)
                if rtype is None:
                    return
                existing = self.var_type.get(var)
                if existing is None:
                    self.var_type[var] = rtype
                elif existing != rtype:
                    # conflicting assignments -> discard
                    self.discarded.add(var)
                    self.var_type.pop(var, None)

            # Stop at nested scopes
            def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # type: ignore[override]
                return False

            def visit_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> bool:  # type: ignore[override]
                return False

            def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # type: ignore[override]
                return False

            def visit_Lambda(self, node: cst.Lambda) -> bool:  # type: ignore[override]
                return False

            def visit_Assign(self, node: cst.Assign) -> None:  # type: ignore[override]
                # Handle simple form: a = Call(...)
                if len(node.targets) != 1:
                    return
                target = node.targets[0].target
                self._record_assignment(target, node.value)

        class AddReturnTypesTransformer(cst.CSTTransformer):
            def __init__(self, known_types: set[str]) -> None:
                super().__init__()
                self.known_types = known_types

            def _infer_return_expr_type(
                self, expr: cst.BaseExpression, var_types: dict[str, str]
            ) -> str | None:
                # Literal simple types
                lit = _infer_literal_type(expr)
                if lit is not None:
                    return lit

                # Call to a known class
                if isinstance(expr, cst.Call):
                    func = expr.func
                    if (
                        isinstance(func, cst.Name)
                        and func.value in self.known_types
                        and func.value[:1].isupper()
                    ):
                        return func.value
                    if isinstance(func, cst.Attribute) and isinstance(
                        func.attr, cst.Name
                    ):
                        attr_name = func.attr.value
                        if attr_name in self.known_types and attr_name[:1].isupper():
                            return attr_name
                    return None

                # Variable referring to a previously inferred var type
                if isinstance(expr, cst.Name):
                    return var_types.get(expr.value)

                return None

            def _infer_for_function(self, func_node: cst.BaseFunctionDef) -> str | None:
                # Collect returns in the function body (non-nested)
                collector = _ReturnCollector()
                # Visit only the immediate body of the function
                if isinstance(func_node, cst.FunctionDef):
                    func_node.body.visit(collector)
                elif isinstance(func_node, cst.AsyncFunctionDef):
                    func_node.body.visit(collector)
                else:
                    return None
                # If no return statements -> None
                if not collector.returns:
                    return "None"

                # Build a simple assignment map within the function
                fac = _FunctionAssignCollector(self.known_types)
                if isinstance(func_node, cst.FunctionDef):
                    func_node.body.visit(fac)
                elif isinstance(func_node, cst.AsyncFunctionDef):
                    func_node.body.visit(fac)

                kinds: set[str] = set()
                for r in collector.returns:
                    if r.value is None:
                        kinds.add("None")
                        continue
                    inferred = self._infer_return_expr_type(r.value, fac.var_type)
                    if inferred is None:
                        return None
                    kinds.add(inferred)

                if len(kinds) == 1:
                    return next(iter(kinds))
                return None

            def leave_FunctionDef(
                self,
                original_node: cst.FunctionDef,
                updated_node: cst.FunctionDef,
            ) -> cst.FunctionDef:
                if updated_node.returns is None:
                    rtype = self._infer_for_function(original_node)
                    if rtype is not None:
                        return updated_node.with_changes(
                            returns=cst.Annotation(annotation=cst.Name(rtype))
                        )
                return updated_node

            def leave_AsyncFunctionDef(
                self,
                original_node: cst.AsyncFunctionDef,
                updated_node: cst.AsyncFunctionDef,
            ) -> cst.AsyncFunctionDef:
                if updated_node.returns is None:
                    rtype = self._infer_for_function(original_node)
                    if rtype is not None:
                        return updated_node.with_changes(
                            returns=cst.Annotation(annotation=cst.Name(rtype))
                        )
                return updated_node

        try:
            module = cst.parse_module(src)
        except Exception:
            # If parsing fails for any reason, return the original source unchanged
            return src

        # Collect known simple type names from the module
        ktc = _KnownTypesCollector()
        module.visit(ktc)

        new_module = module.visit(AddReturnTypesTransformer(ktc.known))
        return new_module.code
