from __future__ import annotations

from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType

from .abstract_python_file_operation import AbstractPythonFileOperation


class PythonAddReturnTypesOperation(AbstractPythonFileOperation):
    """Annotate return types for functions lacking them when trivially inferable.

    Phase 1: annotate -> None, -> bool, -> str, -> int, -> float when all return
    statements in a function agree on one of these literal types.

    Triggered by config: { "python": ["add_return_types"] }.
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )

        return PythonConfigOption.OPTION_NAME_ADD_RETURN_TYPES

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        """Add a return annotation to def lines where a simple literal type is inferable.

        Logic is inlined here (previously in helpers.source.source_annotate_simple_returns).
        """
        import libcst as cst

        src = cls._read_current_str_or_fail(target)

        # We implement type inference and rewriting using LibCST to ensure
        # robust, formatting-preserving edits. Only the simple types are
        # inferred: None, bool, str, int, float.

        def infer_simple_return_type_from_returns(
            returns: list[cst.Return],
        ) -> str | None:
            # No return statements => implicitly returns None
            if not returns:
                return "None"

            kinds: set[str] = set()
            for r in returns:
                val = r.value
                if val is None:
                    kinds.add("None")
                elif isinstance(val, cst.Name):
                    # True/False/None are represented as Name in LibCST
                    if val.value in ("True", "False"):
                        kinds.add("bool")
                    elif val.value == "None":
                        kinds.add("None")
                    else:
                        return None
                elif isinstance(val, cst.SimpleString):
                    kinds.add("str")
                elif isinstance(val, cst.Integer):
                    kinds.add("int")
                elif isinstance(val, cst.Float):
                    kinds.add("float")
                else:
                    return None

            if len(kinds) == 1:
                return next(iter(kinds))
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

        class AddReturnTypesTransformer(cst.CSTTransformer):
            def _infer_for_function(self, func_node: cst.BaseFunctionDef) -> str | None:
                collector = _ReturnCollector()
                # Visit only the immediate body of the function
                if isinstance(func_node, cst.FunctionDef):
                    func_node.body.visit(collector)
                elif isinstance(func_node, cst.AsyncFunctionDef):
                    func_node.body.visit(collector)
                else:
                    return None
                return infer_simple_return_type_from_returns(collector.returns)

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

        new_module = module.visit(AddReturnTypesTransformer())
        return new_module.code

    def describe_before(self) -> str:
        return "Some Python functions are missing obvious return type annotations."

    def describe_after(self) -> str:
        return "Functions have been annotated with simple return types where obvious."

    def description(self) -> str:
        return "Add simple return type annotations (None/bool/str/int/float) when trivially inferable."
