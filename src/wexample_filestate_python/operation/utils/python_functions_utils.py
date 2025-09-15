from __future__ import annotations

from dataclasses import dataclass

import libcst as cst


def collect_module_function_groups(
    module: cst.Module,
) -> list[tuple[int, FunctionGroup]]:
    """Collect top-level functions into groups, preserving overload sequences.

    A group is formed by consecutive FunctionDef nodes with the same name when
    the first N-1 have @overload and the last is the implementation (may or may not
    have @overload in stub-only modules). If there are multiple consecutive
    @overload for a name but no implementation following, they still form a group.
    """
    groups: list[tuple[int, FunctionGroup]] = []
    i = 0
    body = module.body
    n = len(body)
    while i < n:
        node = body[i]
        if isinstance(node, cst.FunctionDef):
            name = _func_name(node)
            j = i + 1
            collected: list[cst.FunctionDef] = [node]
            # collect further overloads of the same name that are directly consecutive
            while j < n:
                next_node = body[j]
                if (
                    isinstance(next_node, cst.FunctionDef)
                    and _func_name(next_node) == name
                ):
                    collected.append(next_node)
                    j += 1
                    continue
                break
            groups.append((i, FunctionGroup(name=name, nodes=tuple(collected))))
            i = j
            continue
        i += 1
    return groups


def module_functions_sorted_before_classes(module: cst.Module) -> bool:
    """Check if all function groups appear before the first class in the module."""
    first_class_index = None
    for idx, node in enumerate(module.body):
        if isinstance(node, cst.ClassDef):
            first_class_index = idx
            break
    if first_class_index is None:
        return True
    # Find first function index
    for idx, node in enumerate(module.body):
        if isinstance(node, cst.FunctionDef):
            return idx < first_class_index
    return True


def reorder_module_functions(module: cst.Module) -> cst.Module:
    """Reorder module-level functions: group, sort (public then private), and place before classes.

    Keeps overload groups intact and preserves each group's leading_lines on its first function.
    """
    groups_with_idx = collect_module_function_groups(module)
    if not groups_with_idx:
        return module

    # Extract groups in original order
    groups = [g for _, g in groups_with_idx]

    # If there is only functions and no classes or their order already correct and sorted, skip?
    # We'll compute a new ordering and compare.
    sorted_groups = sort_function_groups(groups)

    # Remove all function nodes from body
    remove_indices = []
    for idx, g in groups_with_idx:
        remove_indices.extend(range(idx, idx + len(g.nodes)))
    remove_indices = sorted(set(remove_indices))

    new_body: list[cst.CSTNode] = []
    for idx, node in enumerate(module.body):
        if idx in remove_indices:
            continue
        new_body.append(node)

    # Determine insertion index using an anchor strategy:
    # - Find the index of the FIRST function definition in the original module
    # - Reinsert the whole (sorted) functions block at that original position
    #   (adjusted for removals). This avoids moving unrelated code like type
    #   aliases or sys.path mutations and preserves the developer's chosen
    #   placement of the function block.
    def _is_main_guard(node: cst.CSTNode) -> bool:
        if not isinstance(node, cst.If):
            return False
        test = node.test
        # Match patterns like: if __name__ == "__main__":
        if isinstance(test, cst.Comparison):
            left = test.left
            comps = test.comparisons
            if (
                len(comps) == 1
                and isinstance(left, cst.Name)
                and left.value == "__name__"
            ):
                comp = comps[0]
                # operator should be ==
                if isinstance(comp.operator, cst.Equal):
                    right = comp.comparator
                    if isinstance(right, cst.SimpleString):
                        val = (
                            right.evaluated_value
                            if hasattr(right, "evaluated_value")
                            else right.value.strip("\"'")
                        )
                        return val == "__main__" or right.value.strip() in (
                            "'__main__'",
                            '"__main__"',
                        )
        return False

    # Anchor = index of first function in original body
    first_func_index: int | None = None
    for idx, node in enumerate(module.body):
        if isinstance(node, cst.FunctionDef):
            first_func_index = idx
            break

    if first_func_index is None:
        # No functions at module level
        return module

    # Adjust anchor for removed nodes
    removed_before_anchor = sum(1 for i in remove_indices if i < first_func_index)
    insert_at = first_func_index - removed_before_anchor

    # Keep __main__ guard last: if we somehow would insert after it, clamp to its position
    for idx, node in enumerate(new_body):
        if _is_main_guard(node) and insert_at > idx:
            insert_at = idx
            break

    # Ensure functions come before the first class if any
    first_class_index = None
    for idx, node in enumerate(new_body):
        if isinstance(node, cst.ClassDef):
            first_class_index = idx
            break
    if first_class_index is not None and insert_at > first_class_index:
        insert_at = first_class_index

    # Build function nodes preserving each group's comments/spacing on first element
    rebuilt_functions: list[cst.CSTNode] = []
    for g in sorted_groups:
        # Preserve leading_lines of the original first node in the group
        original_first_leading = g.nodes[0].leading_lines
        for k, fn in enumerate(g.nodes):
            if k == 0:
                rebuilt_functions.append(
                    fn.with_changes(leading_lines=original_first_leading)
                )
            else:
                rebuilt_functions.append(fn.with_changes(leading_lines=[]))

    # Insert functions as a contiguous block
    new_body[insert_at:insert_at] = rebuilt_functions

    return module.with_changes(body=new_body)


def sort_function_groups(groups: list[FunctionGroup]) -> list[FunctionGroup]:
    """Sort groups by public (A–Z) then private (_*), each alphabetically case-insensitive."""
    public = [g for g in groups if not _is_private_name(g.name)]
    private = [g for g in groups if _is_private_name(g.name)]
    public.sort(key=lambda g: g.name.lower())
    private.sort(key=lambda g: g.name.lower())
    return public + private


def _func_name(fn: cst.FunctionDef) -> str:
    return fn.name.value


def _has_overload_decorator(fn: cst.FunctionDef) -> bool:
    if fn.decorators:
        return any(_is_overload_decorator(d) for d in fn.decorators)
    return False


def _is_overload_decorator(dec: cst.Decorator) -> bool:
    expr = dec.decorator
    # @overload
    if isinstance(expr, cst.Name) and expr.value == "overload":
        return True
    # @typing.overload
    if isinstance(expr, cst.Attribute):
        if isinstance(expr.attr, cst.Name) and expr.attr.value == "overload":
            return True
    return False


def _is_private_name(name: str) -> bool:
    return name.startswith("_")


@dataclass(frozen=True)
class FunctionGroup:
    name: str
    nodes: tuple[cst.FunctionDef, ...]
