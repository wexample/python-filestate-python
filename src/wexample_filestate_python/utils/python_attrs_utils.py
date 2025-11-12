from __future__ import annotations

import libcst as cst


def fix_attrs_kw_only(module: cst.Module) -> cst.Module:
    """Ensure attrs decorators always use kw_only=True.

    This applies to:
    - @attrs.define
    - @attr.s
    - @attrs.frozen
    """

    class AttrsKwOnlyFixer(cst.CSTTransformer):
        def leave_Decorator(
            self, original_node: cst.Decorator, updated_node: cst.Decorator
        ) -> cst.Decorator:
            # Check if this is an attrs decorator
            if not _is_attrs_decorator(updated_node):
                return updated_node

            # Get the decorator call
            if isinstance(updated_node.decorator, cst.Call):
                call = updated_node.decorator

                # Check if kw_only is already present
                has_kw_only = _has_kw_only_arg(call)

                if not has_kw_only:
                    # Add kw_only=True to the call
                    new_args = list(call.args)
                    kw_only_arg = cst.Arg(
                        keyword=cst.Name("kw_only"), value=cst.Name("True")
                    )
                    new_args.append(kw_only_arg)

                    new_call = call.with_changes(args=new_args)
                    return updated_node.with_changes(decorator=new_call)
                else:
                    # Check if kw_only is set to False and change it to True
                    new_args = []
                    for arg in call.args:
                        if (
                            isinstance(arg.keyword, cst.Name)
                            and arg.keyword.value == "kw_only"
                            and isinstance(arg.value, cst.Name)
                            and arg.value.value == "False"
                        ):
                            # Change False to True
                            new_arg = arg.with_changes(value=cst.Name("True"))
                            new_args.append(new_arg)
                        else:
                            new_args.append(arg)

                    if new_args != list(call.args):
                        new_call = call.with_changes(args=new_args)
                        return updated_node.with_changes(decorator=new_call)

            elif isinstance(updated_node.decorator, (cst.Name, cst.Attribute)):
                # Decorator without parentheses, add them with kw_only=True
                kw_only_arg = cst.Arg(
                    keyword=cst.Name("kw_only"), value=cst.Name("True")
                )

                new_call = cst.Call(func=updated_node.decorator, args=[kw_only_arg])
                return updated_node.with_changes(decorator=new_call)

            return updated_node

    transformer = AttrsKwOnlyFixer()
    modified_module = module.visit(transformer)

    return modified_module


def _has_kw_only_arg(call: cst.Call) -> bool:
    """Check if the call already has a kw_only argument."""
    for arg in call.args:
        if isinstance(arg.keyword, cst.Name) and arg.keyword.value == "kw_only":
            return True
    return False


def _is_attrs_decorator(decorator: cst.Decorator) -> bool:
    """Check if decorator is an attrs decorator (@attrs.define, @attr.s, etc.)."""
    # Get the base decorator (without call)
    base_decorator = decorator.decorator
    if isinstance(base_decorator, cst.Call):
        base_decorator = base_decorator.func

    # Check for @attrs.define, @attrs.frozen, etc.
    if isinstance(base_decorator, cst.Attribute):
        if (
            isinstance(base_decorator.value, cst.Name)
            and base_decorator.value.value == "attrs"
            and isinstance(base_decorator.attr, cst.Name)
            and base_decorator.attr.value in ("define", "frozen")
        ):
            return True

    # Check for @attr.s
    if isinstance(base_decorator, cst.Attribute):
        if (
            isinstance(base_decorator.value, cst.Name)
            and base_decorator.value.value == "attr"
            and isinstance(base_decorator.attr, cst.Name)
            and base_decorator.attr.value == "s"
        ):
            return True

    return False
