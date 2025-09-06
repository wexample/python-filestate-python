from __future__ import annotations

from typing import DefaultDict, ClassVar

import libcst as cst


class PythonUsageCollector(cst.CSTVisitor):
    """Collect usage of imported names across three categories:
    - A: runtime usages inside function/method bodies (class calls, typing.cast target)
    - B: class-level property type annotations
    - C: type-only annotations in params/returns/module-level AnnAssign

    The collector mutates the provided buckets so the caller can reuse shared storage.
    """

    DEFAULT_CAST_FUNCTION_CANDIDATES: ClassVar[set[str]] = {"cast"}

    def __init__(
        self,
        imported_value_names: set[str],
        functions_needing_local: DefaultDict[str, set[str]],
        used_in_B: set[str],
        used_in_C_annot: set[str],
        cast_type_names_anywhere: set[str],
        cast_function_candidates: set[str] | None = None,
    ) -> None:
        super().__init__()
        self.imported_value_names = imported_value_names
        self.functions_needing_local = functions_needing_local
        self.used_in_B = used_in_B
        self.used_in_C_annot = used_in_C_annot
        self.cast_type_names_anywhere = cast_type_names_anywhere
        self.cast_function_candidates = (
            set(self.DEFAULT_CAST_FUNCTION_CANDIDATES)
            if cast_function_candidates is None
            else cast_function_candidates
        )

        self.class_stack: list[str] = []
        self.func_stack: list[str] = []

    # ----- Stack management -----
    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # type: ignore[override]
        self.class_stack.append(node.name.value)
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # type: ignore[override]
        self.class_stack.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # type: ignore[override]
        self.func_stack.append(self._qualified_func_name(node.name.value))
        # Record return annotation for C
        if node.returns is not None:
            self._record_type_names(node.returns.annotation, self.used_in_C_annot)
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # type: ignore[override]
        self.func_stack.pop()

    def visit_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> bool:  # type: ignore[override]
        self.func_stack.append(self._qualified_func_name(node.name.value))
        # Record return annotation for C
        if node.returns is not None:
            self._record_type_names(node.returns.annotation, self.used_in_C_annot)
        return True

    def leave_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> None:  # type: ignore[override]
        self.func_stack.pop()

    # ----- A: runtime usages inside functions -----
    def visit_Call(self, node: cst.Call) -> None:  # type: ignore[override]
        if not self.func_stack:
            return
        func = node.func
        if isinstance(func, cst.Name):
            callee = func.value
            # class constructor call
            if callee in self.imported_value_names and callee[:1].isupper():
                self.functions_needing_local[self.func_stack[-1]].add(callee)
                return
            # typing.cast(x, MyClass) when used as bare `cast(...)`
            if (callee in self.cast_function_candidates or "cast" in callee.lower()) and node.args and len(node.args) >= 1:
                type_arg = node.args[0].value
                # Collect any imported names appearing anywhere inside the type expression
                names = self._collect_names_from_type_expr(second)
                names = self._collect_names_from_type_expr(type_arg)
                for n in names:
                    # Always record for module-wide exclusion from TYPE_CHECKING
                    self.cast_type_names_anywhere.add(n)
                    # Always schedule local import for this function; localizer will filter if module cannot be resolved
                    if self.func_stack:
                        self.functions_needing_local[self.func_stack[-1]].add(n)
                return
        elif isinstance(func, cst.Attribute):
            # typing.cast(...) or pkg.cast(...)
            if (
                isinstance(func.attr, cst.Name)
                and (func.attr.value in self.cast_function_candidates or "cast" in func.attr.value.lower())
                and node.args
                and len(node.args) >= 1
            ):
                second = node.args[1].value
                names = self._collect_names_from_type_expr(second)
                type_arg = node.args[0].value
                names = self._collect_names_from_type_expr(type_arg)
                for n in names:
                    self.cast_type_names_anywhere.add(n)
                    if self.func_stack:
                        self.functions_needing_local[self.func_stack[-1]].add(n)
                return

    # ----- B: class-level property annotations -----
    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:  # type: ignore[override]
        if not self.class_stack:
            # module-level annotated assignment -> C
            self._record_type_names(node.annotation.annotation, self.used_in_C_annot)
            return
        self._record_type_names(node.annotation.annotation, self.used_in_B)

    # Also treat class-level simple assignments where RHS references imported names as B.
    # Example: SERVICE_CLASS = GithubRemote
    def visit_Assign(self, node: cst.Assign) -> None:  # type: ignore[override]
        if not self.class_stack:
            return
        # Record any imported names appearing in the value expression as B
        try:
            value = node.value
        except Exception:
            return
        self._walk_expr_for_names(value, self.used_in_B)

    # ----- C: function param annotations -----
    def visit_Param(self, node: cst.Param) -> None:  # type: ignore[override]
        if node.annotation is not None:
            self._record_type_names(node.annotation.annotation, self.used_in_C_annot)

    # ----- internals -----
    def _qualified_func_name(self, base: str) -> str:
        return ".".join(self.class_stack + [base]) if self.class_stack else base

    def _record_type_names(self, ann: cst.BaseExpression, bucket: set[str]) -> None:
        if isinstance(ann, cst.Name):
            if ann.value in self.imported_value_names:
                bucket.add(ann.value)
        elif isinstance(ann, cst.Subscript):
            self._walk_expr_for_names(ann.value, bucket)
            for e in ann.slice:
                if isinstance(e, cst.SubscriptElement) and isinstance(
                    e.slice, cst.Index
                ):
                    self._walk_expr_for_names(e.slice.value, bucket)
        else:
            self._walk_expr_for_names(ann, bucket)

    def _walk_expr_for_names(self, expr: cst.BaseExpression, bucket: set[str]) -> None:
        if isinstance(expr, cst.Name):
            if expr.value in self.imported_value_names:
                bucket.add(expr.value)
        elif isinstance(expr, cst.Attribute):
            if (
                isinstance(expr.attr, cst.Name)
                and expr.attr.value in self.imported_value_names
            ):
                bucket.add(expr.attr.value)
        elif isinstance(expr, cst.Subscript):
            self._walk_expr_for_names(expr.value, bucket)
            for e in expr.slice:
                if isinstance(e, cst.SubscriptElement) and isinstance(
                    e.slice, cst.Index
                ):
                    self._walk_expr_for_names(e.slice.value, bucket)

    # Collect names inside a type expression (Name, Attribute tail, Subscript args)
    def _collect_names_from_type_expr(self, expr: cst.BaseExpression) -> set[str]:
        acc: set[str] = set()
        # Handle forward-ref style: cast("Foo", x) or cast("dict[str, Foo]", x)
        if isinstance(expr, cst.SimpleString):
            try:
                # Remove surrounding quotes; libcst handles raw string quotes
                text = expr.evaluated_value
                parsed = cst.parse_expression(text)
                self._walk_expr_for_names(parsed, acc)
                return acc
            except Exception:
                return acc
        self._walk_expr_for_names(expr, acc)
        return acc
