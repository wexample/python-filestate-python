from __future__ import annotations

import libcst as cst


def fix_attrs_kw_only(module: cst.Module) -> cst.Module:
    """Ensure attrs decorators always use kw_only=True.

    This applies to:
    - @attrs.define
    - @attr.s
    - @attrs.frozen
    """
    return module.visit(_AttrsKwOnlyFixer())


def _has_kw_only_arg(call: cst.Call) -> bool:
    """Check if the call already has a kw_only argument."""
    return any(
        isinstance(arg.keyword, cst.Name) and arg.keyword.value == "kw_only"
        for arg in call.args
    )


def _is_attrs_decorator(decorator: cst.Decorator) -> bool:
    """Check if decorator is an attrs decorator (@attrs.define, @attr.s, etc.)."""
    base_decorator = decorator.decorator
    if isinstance(base_decorator, cst.Call):
        base_decorator = base_decorator.func

    # Both attrs.*/attr.s paths share the same outer isinstance checks
    if isinstance(base_decorator, cst.Attribute) and isinstance(
        base_decorator.value, cst.Name
    ):
        module_name = base_decorator.value.value
        attr_name = base_decorator.attr.value
        return (module_name == "attrs" and attr_name in ("define", "frozen")) or (
            module_name == "attr" and attr_name == "s"
        )

    return False


class _AttrsKwOnlyFixer(cst.CSTTransformer):
    """CST transformer: ensures attrs decorators always carry kw_only=True."""

    def leave_Decorator(
        self, original_node: cst.Decorator, updated_node: cst.Decorator
    ) -> cst.Decorator:
        if not _is_attrs_decorator(updated_node):
            return updated_node

        if isinstance(updated_node.decorator, cst.Call):
            call = updated_node.decorator

            if not _has_kw_only_arg(call):
                # Add kw_only=True — tuple unpack avoids an intermediate list
                kw_only_arg = cst.Arg(
                    keyword=cst.Name("kw_only"), value=cst.Name("True")
                )
                new_call = call.with_changes(args=(*call.args, kw_only_arg))
                return updated_node.with_changes(decorator=new_call)

            # kw_only already present — flip False → True if needed
            changed = False
            new_args = []
            for arg in call.args:
                if (
                    isinstance(arg.keyword, cst.Name)
                    and arg.keyword.value == "kw_only"
                    and isinstance(arg.value, cst.Name)
                    and arg.value.value == "False"
                ):
                    new_args.append(arg.with_changes(value=cst.Name("True")))
                    changed = True
                else:
                    new_args.append(arg)

            if changed:
                new_call = call.with_changes(args=new_args)
                return updated_node.with_changes(decorator=new_call)

        elif isinstance(updated_node.decorator, (cst.Name, cst.Attribute)):
            # Bare decorator (no parens) — wrap it in a Call with kw_only=True
            kw_only_arg = cst.Arg(
                keyword=cst.Name("kw_only"), value=cst.Name("True")
            )
            new_call = cst.Call(func=updated_node.decorator, args=[kw_only_arg])
            return updated_node.with_changes(decorator=new_call)

        return updated_node
