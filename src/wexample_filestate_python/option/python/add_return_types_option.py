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

        from wexample_filestate_python.utils.cst_cache import (
            get_python_source_and_module,
        )

        src, module = get_python_source_and_module(target)

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

        def _infer_class_call_type(
            call: cst.Call, known_types: set[str]
        ) -> str | None:
            """Return the class name if `call` instantiates a known type.

            Recognizes `Foo()` and `module.Foo()` shapes; requires the matched
            name to be uppercase-first to stay conservative. Single source of
            truth shared by the assignment collector and the return-expression
            transformer.
            """
            func = call.func
            if isinstance(func, cst.Name):
                if func.value in known_types and func.value[:1].isupper():
                    return func.value
                return None
            if isinstance(func, cst.Attribute) and isinstance(func.attr, cst.Name):
                attr_name = func.attr.value
                if attr_name in known_types and attr_name[:1].isupper():
                    return attr_name
            return None

        class _ReturnCollector(cst.CSTVisitor):
            def __init__(self) -> None:
                self.returns: list[cst.Return] = []
                # A function with any `yield` / `yield from` is a generator —
                # its real return type is Iterator[X], not whatever the return
                # statements imply. We can't infer Iterator[X] from this simple
                # pass, so we record the flag and bail out at the caller.
                self.has_yield: bool = False

            # Do not descend into nested scopes that could have their own returns
            def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # type: ignore[override]
                return False

            def visit_Lambda(self, node: cst.Lambda) -> bool:  # type: ignore[override]
                return False

            def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # type: ignore[override]
                return False

            def visit_Return(self, node: cst.Return) -> None:  # type: ignore[override]
                self.returns.append(node)

            def visit_Yield(self, node: cst.Yield) -> None:  # type: ignore[override]
                # libcst represents `yield from X` as a Yield whose value is
                # `cst.From(item=X)`, so this single hook catches both forms.
                self.has_yield = True

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
                rtype = _infer_class_call_type(value, self.known_types)
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
                    return _infer_class_call_type(expr, self.known_types)

                # Variable referring to a previously inferred var type
                if isinstance(expr, cst.Name):
                    return var_types.get(expr.value)

                return None

            def _infer_for_function(self, func_node: cst.FunctionDef) -> str | None:
                # Collect returns in the function body (non-nested)
                collector = _ReturnCollector()
                if not isinstance(func_node, cst.FunctionDef):
                    return None
                func_node.body.visit(collector)
                # Generator: never annotate via this simple pass. The function
                # actually returns Iterator[X] / Generator[X, ...], which we
                # can't infer here — leave it unannotated for a human to fill.
                if collector.has_yield:
                    return None
                # If no return statements -> None
                if not collector.returns:
                    return "None"

                # Build a simple assignment map within the function
                fac = _FunctionAssignCollector(self.known_types)
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

        # Collect known simple type names from the module
        ktc = _KnownTypesCollector()
        module.visit(ktc)

        new_module = module.visit(AddReturnTypesTransformer(ktc.known))
        return new_module.code
