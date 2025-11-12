from __future__ import annotations

from typing import ClassVar, DefaultDict

import libcst as cst

from wexample_filestate_python.utils.relocate_imports import PythonParserImportIndex


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
        future_annotations_enabled: bool = True,
        idx: PythonParserImportIndex | None = None,
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
        self.future_annotations_enabled = future_annotations_enabled
        self.idx = idx

        self.class_stack: list[str] = []
        self.func_stack: list[str] = []
        self._in_annotation_stack: list[bool] = []
        self._in_decorator_stack: list[bool] = []
        self._in_param_default_stack: list[bool] = []
        self._in_param_annot_stack: list[bool] = []

    def leave_Annotation(self, node: cst.Annotation) -> None:  # type: ignore[override]
        if self._in_annotation_stack:
            self._in_annotation_stack.pop()

    def leave_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> None:  # type: ignore[override]
        self.func_stack.pop()

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # type: ignore[override]
        self.class_stack.pop()

    def leave_Decorator(self, node: cst.Decorator) -> None:  # type: ignore[override]
        if self._in_decorator_stack:
            self._in_decorator_stack.pop()

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # type: ignore[override]
        self.func_stack.pop()

    def leave_Param(self, node: cst.Param) -> None:  # type: ignore[override]
        if self._in_param_default_stack:
            self._in_param_default_stack.pop()
        if self._in_param_annot_stack:
            self._in_param_annot_stack.pop()

    # ----- B: class-level property annotations -----
    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:  # type: ignore[override]
        if not self.class_stack:
            # module-level annotated assignment -> C
            self._record_type_names(node.annotation.annotation, self.used_in_C_annot)
            return
        # class-level annotated assignment: if future annotations are enabled, treat as type-only (C)
        # otherwise, require availability at class definition time (B)
        if self.future_annotations_enabled:
            self._record_type_names(node.annotation.annotation, self.used_in_C_annot)
        else:
            self._record_type_names(node.annotation.annotation, self.used_in_B)
        # Additionally, if the annotated assignment has a default value at class level,
        # any imported names referenced in that value are needed at class definition time.
        try:
            if node.value is not None:
                self._walk_expr_for_names(node.value, self.used_in_B)
        except Exception:
            pass

    # Track annotation context to avoid misclassifying annotation names as runtime
    def visit_Annotation(self, node: cst.Annotation) -> bool:  # type: ignore[override]
        self._in_annotation_stack.append(True)
        return True

    # Prevent visiting keyword argument names in function calls
    def visit_Arg(self, node: cst.Arg) -> bool:  # type: ignore[override]
        # Only visit the value, not the keyword name
        # e.g., in foo(verbosity=123), visit 123 but not 'verbosity'
        if node.value:
            node.value.visit(self)
        return False  # Don't visit children (especially node.keyword)

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

    def visit_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> bool:  # type: ignore[override]
        self.func_stack.append(self._qualified_func_name(node.name.value))
        # Record return annotation for C
        if node.returns is not None:
            self._record_type_names(node.returns.annotation, self.used_in_C_annot)
        return True

    # Track when we're inside an Attribute to avoid treating attribute names as bare names
    def visit_Attribute(self, node: cst.Attribute) -> bool:  # type: ignore[override]
        # Visit the value (left side) but not the attr (right side)
        # This prevents visit_Name from being called on the attribute name itself
        # e.g., in self.verbosity, we visit 'self' but not 'verbosity'
        if isinstance(node.value, cst.BaseExpression):
            node.value.visit(self)
        return False  # Don't visit children (especially node.attr)

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
            if (
                (callee in self.cast_function_candidates or "cast" in callee.lower())
                and node.args
                and len(node.args) >= 1
            ):
                type_arg = node.args[0].value
                # Collect any imported names appearing anywhere inside the type expression
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
                and (
                    func.attr.value in self.cast_function_candidates
                    or "cast" in func.attr.value.lower()
                )
                and node.args
                and len(node.args) >= 1
            ):
                type_arg = node.args[0].value
                names = self._collect_names_from_type_expr(type_arg)
                for n in names:
                    self.cast_type_names_anywhere.add(n)
                    if self.func_stack:
                        self.functions_needing_local[self.func_stack[-1]].add(n)
                return

    # ----- Stack management -----
    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # type: ignore[override]
        self.class_stack.append(node.name.value)
        # Treat symbols in the inheritance list as B (must be available at class creation)
        for base in node.bases:
            try:
                self._walk_expr_for_names(base.value, self.used_in_B)
            except Exception:
                pass
        return True

    # Track decorator context and record decorator names as module-level usage (B)
    # Decorators are evaluated at function/class definition time, not at runtime
    def visit_Decorator(self, node: cst.Decorator) -> bool:  # type: ignore[override]
        self._in_decorator_stack.append(True)
        # Walk the decorator expression to find imported names
        # e.g., @command, @option(...), @middleware(middleware=PackageSuiteMiddleware)
        try:
            self._walk_expr_for_names(node.decorator, self.used_in_B)
        except Exception:
            pass
        return True

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # type: ignore[override]
        self.func_stack.append(self._qualified_func_name(node.name.value))
        # Record return annotation for C
        if node.returns is not None:
            self._record_type_names(node.returns.annotation, self.used_in_C_annot)
        return True

    # Treat bare Name usage inside function bodies as runtime usage (A)
    def visit_Name(self, node: cst.Name) -> None:  # type: ignore[override]
        if not self.func_stack:
            return
        if (
            self._in_annotation_stack
            or self._in_decorator_stack
            or any(self._in_param_default_stack)
            or any(self._in_param_annot_stack)
        ):
            return
        val = node.value
        # Do not treat 'cast' identifier as runtime usage; keep typing at module level
        if val == "cast":
            return
        if val in self.imported_value_names:
            # Resolve module to avoid misclassifying annotation-only names like Mapping
            resolved_mod = None
            try:
                if hasattr(self, "idx") and getattr(self, "idx") is not None:  # type: ignore[attr-defined]
                    resolved_mod = getattr(self, "idx").name_to_from.get(val, (None, None))[0]  # type: ignore[index]
            except Exception:
                resolved_mod = None
            # Skip if module is unknown or belongs to typing/collections.abc
            # Also skip bare imports (import os.path) which cannot be localized
            if resolved_mod in (None, "typing", "collections", "collections.abc"):
                # For bare imports (resolved_mod is None), mark as module-level usage
                # since we cannot relocate them (can't do "from os import path" locally)
                if resolved_mod is None and val in self.imported_value_names:
                    self.used_in_B.add(val)
                return
            self.functions_needing_local[self.func_stack[-1]].add(val)

    # Track param default context; defaults are evaluated at definition time (module init), not runtime
    def visit_Param(self, node: cst.Param) -> bool:  # type: ignore[override]
        has_default = node.default is not None
        self._in_param_default_stack.append(has_default)
        # Mark that we are in a parameter annotation while traversing children
        in_annot = node.annotation is not None
        self._in_param_annot_stack.append(in_annot)
        # Record parameter annotation types into C (annotation usage)
        if node.annotation is not None:
            self._record_type_names(node.annotation.annotation, self.used_in_C_annot)
        # Names in defaults are needed at definition time: treat as B
        if has_default:
            try:
                # Collect base identifiers even if not recognized as imported yet
                collected: set[str] = set()

                def _collect_base_names(expr: cst.BaseExpression) -> None:
                    if isinstance(expr, cst.Name):
                        collected.add(expr.value)
                    elif isinstance(expr, cst.Attribute):
                        _collect_base_names(expr.value)
                    elif isinstance(expr, cst.Subscript):
                        _collect_base_names(expr.value)
                        for e in expr.slice:
                            if isinstance(e, cst.SubscriptElement) and isinstance(
                                e.slice, cst.Index
                            ):
                                _collect_base_names(e.slice.value)

                _collect_base_names(node.default)
                self.used_in_B.update(collected)
            except Exception:
                pass
        # We still record annotation as C elsewhere
        return True

    # ----- C: function param annotations -----
    def visit_Param(self, node: cst.Param) -> None:  # type: ignore[override]
        if node.annotation is not None:
            self._record_type_names(node.annotation.annotation, self.used_in_C_annot)

    # Fallback: explicitly scan Parameters node for defaults (some environments may not trigger visit_Param)
    def visit_Parameters(self, node: cst.Parameters) -> bool:  # type: ignore[override]
        try:
            self.func_stack[-1] if self.func_stack else "<module>"
            # Aggregate all parameter-like collections
            all_params: list[cst.Param] = []
            all_params.extend(list(node.params))
            all_params.extend(list(node.posonly_params))
            all_params.extend(list(node.kwonly_params))
            if node.star_arg is not None and isinstance(node.star_arg, cst.Param):
                all_params.append(node.star_arg)
            if node.star_kwarg is not None and isinstance(node.star_kwarg, cst.Param):
                all_params.append(node.star_kwarg)

            for p in all_params:
                has_default = p.default is not None
                if not has_default:
                    continue
                collected: set[str] = set()

                def _collect_base_names(expr: cst.BaseExpression) -> None:
                    if isinstance(expr, cst.Name):
                        collected.add(expr.value)
                    elif isinstance(expr, cst.Attribute):
                        _collect_base_names(expr.value)
                    elif isinstance(expr, cst.Subscript):
                        _collect_base_names(expr.value)
                        for e in expr.slice:
                            if isinstance(e, cst.SubscriptElement) and isinstance(
                                e.slice, cst.Index
                            ):
                                _collect_base_names(e.slice.value)

                _collect_base_names(p.default)  # type: ignore[arg-type]
                self.used_in_B.update(collected)
        except Exception:
            pass
        return True

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

    # ----- internals -----
    def _qualified_func_name(self, base: str) -> str:
        # Include func_stack to distinguish nested functions with the same name
        # e.g., ScreenExample.demo_with_progress_and_confirm._callback vs ScreenExample.example_extended._callback
        return (
            ".".join(self.class_stack + self.func_stack + [base])
            if (self.class_stack or self.func_stack)
            else base
        )

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
            # Walk attribute chain: only record the base name (e.g., TerminalColor in TerminalColor.WHITE)
            # Recurse into value (left side) only
            self._walk_expr_for_names(expr.value, bucket)
            # DO NOT consider the attr name itself (right side) as an imported name to avoid
            # confusion with instance/class attributes like self.verbosity vs imported verbosity
        elif isinstance(expr, cst.BinaryOperation):
            # Handle PEP 604 union types: e.g., Path | None
            # Traverse both sides of the binary operation
            try:
                self._walk_expr_for_names(expr.left, bucket)
            except Exception:
                pass
            try:
                self._walk_expr_for_names(expr.right, bucket)
            except Exception:
                pass
        elif isinstance(expr, cst.Subscript):
            self._walk_expr_for_names(expr.value, bucket)
            for e in expr.slice:
                if isinstance(e, cst.SubscriptElement) and isinstance(
                    e.slice, cst.Index
                ):
                    self._walk_expr_for_names(e.slice.value, bucket)
        elif isinstance(expr, cst.Call):
            # Walk into function calls to detect names in arguments
            # e.g., private_field(default=VerbosityLevel.DEFAULT)
            self._walk_expr_for_names(expr.func, bucket)
            for arg in expr.args:
                self._walk_expr_for_names(arg.value, bucket)
        elif isinstance(expr, cst.List):
            # Walk into list literals to detect names in elements
            # e.g., validators=[RegexValidator(...)]
            for element in expr.elements:
                if isinstance(element, cst.Element):
                    self._walk_expr_for_names(element.value, bucket)
        elif isinstance(expr, cst.Tuple):
            # Walk into tuple literals to detect names in elements
            for element in expr.elements:
                if isinstance(element, cst.Element):
                    self._walk_expr_for_names(element.value, bucket)
        elif isinstance(expr, cst.Dict):
            # Walk into dict literals to detect names in keys and values
            for element in expr.elements:
                if isinstance(element, cst.DictElement):
                    self._walk_expr_for_names(element.key, bucket)
                    self._walk_expr_for_names(element.value, bucket)
