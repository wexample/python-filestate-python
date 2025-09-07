from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import libcst as cst
from libcst import matchers as m


def collect_module_function_groups(module: cst.Module) -> List[Tuple[int, FunctionGroup]]:
    """Collect top-level functions into groups, preserving overload sequences.

    A group is formed by consecutive FunctionDef nodes with the same name when
    the first N-1 have @overload and the last is the implementation (may or may not
    have @overload in stub-only modules). If there are multiple consecutive
    @overload for a name but no implementation following, they still form a group.
    """
    groups: List[Tuple[int, FunctionGroup]] = []
    i = 0
    body = module.body
    n = len(body)
    while i < n:
        node = body[i]
        if isinstance(node, cst.FunctionDef):
            name = _func_name(node)
            j = i + 1
            collected: List[cst.FunctionDef] = [node]
            # collect further overloads of the same name that are directly consecutive
            while j < n:
                next_node = body[j]
                if isinstance(next_node, cst.FunctionDef) and _func_name(next_node) == name:
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

    new_body: List[cst.CSTNode] = []
    for idx, node in enumerate(module.body):
        if idx in remove_indices:
            continue
        new_body.append(node)

    # Determine insertion index safely:
    # - Insert before the first non-declaration node (anything that's not
    #   docstring/imports/TYPE_CHECKING/metadata/UPPER_CASE constants)
    # - Classes are considered a barrier (functions must come before classes)
    # - Always insert before the __main__ guard so it remains last
    def _is_main_guard(node: cst.CSTNode) -> bool:
        if not isinstance(node, cst.If):
            return False
        test = node.test
        # Match patterns like: if __name__ == "__main__":
        if isinstance(test, cst.Comparison):
            left = test.left
            comps = test.comparisons
            if len(comps) == 1 and isinstance(left, cst.Name) and left.value == "__name__":
                comp = comps[0]
                # operator should be ==
                if isinstance(comp.operator, cst.Equal):
                    right = comp.comparator
                    if isinstance(right, cst.SimpleString):
                        val = right.evaluated_value if hasattr(right, "evaluated_value") else right.value.strip('"\'')
                        return val == "__main__" or right.value.strip() in ("'__main__'", '"__main__"')
        return False

    METADATA_NAMES = {"__all__", "__version__", "__author__", "__email__", "__license__", "__copyright__", "__title__", "__description__"}

    def _is_docstring_node(node: cst.CSTNode, idx: int) -> bool:
        if idx != 0:
            return False
        if not isinstance(node, cst.SimpleStatementLine):
            return False
        return (
            len(node.body) == 1
            and isinstance(node.body[0], cst.Expr)
            and isinstance(node.body[0].value, cst.SimpleString)
        )

    def _is_import_line(node: cst.CSTNode) -> bool:
        if not isinstance(node, cst.SimpleStatementLine):
            return False
        return any(isinstance(s, (cst.Import, cst.ImportFrom)) for s in node.body)

    def _is_type_checking_if(node: cst.CSTNode) -> bool:
        if not isinstance(node, cst.If):
            return False
        # Matches: if TYPE_CHECKING: or if typing.TYPE_CHECKING:
        return m.matches(
            node,
            m.If(
                test=(
                    m.Name("TYPE_CHECKING")
                    | m.Attribute(value=m.Name("typing"), attr=m.Name("TYPE_CHECKING"))
                )
            ),
        )

    def _is_metadata_or_upper_const(node: cst.CSTNode) -> bool:
        if not isinstance(node, cst.SimpleStatementLine):
            return False
        if len(node.body) != 1:
            return False
        small = node.body[0]
        if isinstance(small, cst.Assign) and len(small.targets) == 1:
            tgt = small.targets[0].target
            if isinstance(tgt, cst.Name):
                name = tgt.value
                return name in METADATA_NAMES or name.isupper()
        if isinstance(small, cst.AnnAssign) and isinstance(small.target, cst.Name):
            name = small.target.value
            return name in METADATA_NAMES or name.isupper()
        return False

    def _is_typing_type_alias(node: cst.CSTNode) -> bool:
        """Detect TypeVar/NewType assignments and TypeAlias annotated assignments.

        Examples kept as declarations:
          SortableType = TypeVar("SortableType")
          UserId = NewType("UserId", int)
          MyAlias: TypeAlias = dict[str, int]
        """
        if not isinstance(node, cst.SimpleStatementLine) or len(node.body) != 1:
            return False
        small = node.body[0]
        # Assign: Name = Call(TypeVar/typing.TypeVar or NewType/typing.NewType)
        if isinstance(small, cst.Assign) and len(small.targets) == 1:
            value = small.value
            if isinstance(value, cst.Call):
                callee = value.func
                # TypeVar or typing.TypeVar
                if isinstance(callee, cst.Name) and callee.value in {"TypeVar", "NewType"}:
                    return True
                if isinstance(callee, cst.Attribute) and isinstance(callee.attr, cst.Name) and callee.attr.value in {"TypeVar", "NewType"}:
                    return True
        # Annotated assignment: Name: TypeAlias = ... (typing.TypeAlias also possible in older versions)
        if isinstance(small, cst.AnnAssign):
            ann = small.annotation.annotation
            if isinstance(ann, cst.Name) and ann.value == "TypeAlias":
                return True
            if isinstance(ann, cst.Attribute) and isinstance(ann.attr, cst.Name) and ann.attr.value == "TypeAlias":
                return True
        return False

    def _is_declaration(node: cst.CSTNode, idx: int) -> bool:
        return (
            _is_docstring_node(node, idx)
            or _is_import_line(node)
            or _is_type_checking_if(node)
            or _is_metadata_or_upper_const(node)
            or _is_typing_type_alias(node)
        )

    # Find main guard index if present
    main_guard_index: Optional[int] = None
    for idx, node in enumerate(new_body):
        if _is_main_guard(node):
            main_guard_index = idx
            break

    # Scan for first barrier: class, main guard, or any non-declaration
    insert_at = len(new_body)
    for idx, node in enumerate(new_body):
        if isinstance(node, cst.ClassDef) or _is_main_guard(node) or not _is_declaration(node, idx):
            insert_at = idx
            break

    # Ensure we don't insert after the __main__ guard
    if main_guard_index is not None and insert_at > main_guard_index:
        insert_at = main_guard_index

    # Build function nodes preserving each group's comments/spacing on first element
    rebuilt_functions: List[cst.CSTNode] = []
    for g in sorted_groups:
        # Preserve leading_lines of the original first node in the group
        original_first_leading = g.nodes[0].leading_lines
        for k, fn in enumerate(g.nodes):
            if k == 0:
                rebuilt_functions.append(fn.with_changes(leading_lines=original_first_leading))
            else:
                rebuilt_functions.append(fn.with_changes(leading_lines=[]))

    # Insert functions as a contiguous block
    new_body[insert_at:insert_at] = rebuilt_functions

    return module.with_changes(body=new_body)


def sort_function_groups(groups: List[FunctionGroup]) -> List[FunctionGroup]:
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
    nodes: Tuple[cst.FunctionDef, ...]
