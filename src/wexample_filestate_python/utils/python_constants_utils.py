from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import libcst as cst

if TYPE_CHECKING:
    from collections.abc import Sequence

FLAG_NAME = "python-constant-sort"


def find_flagged_constant_blocks(
    module: cst.Module, src: str
) -> list[tuple[int, int, list[cst.SimpleStatementLine]]]:
    """Find blocks of contiguous UPPER_CASE assignments following the filestate flag.

    A block starts at the first assignment statement that has the flag in its leading
    comments; it continues with subsequent contiguous constant assignments until a
    blank line or a non-constant statement is found.

    Returns list of tuples (start_index, end_index_exclusive, nodes_in_block)
    where indices refer to module.body positions.
    """
    blocks: list[tuple[int, int, list[cst.SimpleStatementLine]]] = []

    i = 0
    body = module.body
    n = len(body)
    while i < n:
        stmt = body[i]
        if isinstance(stmt, cst.SimpleStatementLine):
            has_flag = _stmt_has_flag(stmt, src) or _prev_line_has_flag(list(body), i)
            if has_flag and _get_simple_assignment_name(stmt) is not None:
                # Start a block at i
                j = i
                nodes: list[cst.SimpleStatementLine] = []
                while j < n:
                    s = body[j]
                    if isinstance(s, cst.SimpleStatementLine):
                        if j != i:
                            # Stop the block ONLY if there is a blank line separation
                            # (an EmptyLine without a comment) among leading_lines.
                            if any(el.comment is None for el in s.leading_lines):
                                break
                        name = _get_simple_assignment_name(s)
                        if name is None:
                            break
                        nodes.append(s)
                        j += 1
                        continue
                    # Stop at any other node
                    break
                if nodes:
                    blocks.append((i, j, nodes))
                    i = j
                    continue
        i += 1

    return blocks


# -------- Class-level support --------
def find_flagged_constant_blocks_in_class(
    classdef: cst.ClassDef, src: str
) -> list[tuple[int, int, list[cst.SimpleStatementLine]]]:
    """Find flagged constant blocks within a class body.

    Returns list of tuples (start_index, end_index_exclusive, nodes_in_block)
    where indices refer to classdef.body.body positions.
    """
    blocks: list[tuple[int, int, list[cst.SimpleStatementLine]]] = []
    body_list = list(classdef.body.body)
    n = len(body_list)
    i = 0
    while i < n:
        item = body_list[i]
        if isinstance(item, cst.SimpleStatementLine):
            has_flag = _stmt_has_flag(item, src) or _prev_line_has_flag(body_list, i)
            if has_flag and _get_simple_assignment_name(item) is not None:
                j = i
                nodes: list[cst.SimpleStatementLine] = []
                while j < n:
                    s = body_list[j]
                    if isinstance(s, cst.SimpleStatementLine):
                        if j != i:
                            # Stop the block ONLY on a blank line (no comment) among leading_lines.
                            if any(el.comment is None for el in s.leading_lines):
                                break
                        name = _get_simple_assignment_name(s)
                        if name is None:
                            break
                        nodes.append(s)
                        j += 1
                        continue
                    break
                if nodes:
                    blocks.append((i, j, nodes))
                    i = j
                    continue
        i += 1
    return blocks


def reorder_flagged_constants(module: cst.Module, src: str) -> cst.Module:
    blocks = find_flagged_constant_blocks(module, src)
    if not blocks:
        return module

    new_body = list(module.body)

    # Process blocks from last to first to keep indices stable
    for start, end, nodes in reversed(blocks):
        sorted_nodes = sort_constants_block(nodes)
        # If unchanged, skip
        if all(a is b for a, b in zip(nodes, sorted_nodes)):
            continue
        # Replace slice
        new_body[start:end] = sorted_nodes

    return module.with_changes(body=new_body)


def reorder_flagged_constants_everywhere(module: cst.Module, src: str) -> cst.Module:
    """Reorder flagged constant blocks at module level and within class bodies."""
    first = reorder_flagged_constants(module, src)
    second = reorder_flagged_constants_in_classes(first, src)
    return second


def reorder_flagged_constants_in_classes(module: cst.Module, src: str) -> cst.Module:
    """Reorder flagged constant blocks inside all class definitions in the module."""
    changed = False
    new_module_body = list(module.body)

    for idx, node in enumerate(new_module_body):
        if isinstance(node, cst.ClassDef):
            class_body_list = list(node.body.body)
            blocks = find_flagged_constant_blocks_in_class(node, src)
            if not blocks:
                continue
            # Apply from last to first within the class body
            for start, end, nodes in reversed(blocks):
                sorted_nodes = sort_constants_block(nodes)
                if all(a is b for a, b in zip(nodes, sorted_nodes)):
                    continue
                class_body_list[start:end] = sorted_nodes
                changed = True
            if changed:
                new_class_body = node.body.with_changes(body=class_body_list)
                new_module_body[idx] = node.with_changes(body=new_class_body)

    if not changed:
        return module
    return module.with_changes(body=new_module_body)


def sort_constants_block(
    nodes: list[cst.SimpleStatementLine],
) -> list[cst.SimpleStatementLine]:
    """Return a new list of nodes sorted by variable name (case-insensitive).

    Preserve the flag comment by attaching it to the first node of the
    sorted block (even if a different node becomes first after sorting),
    and clear leading_lines of subsequent nodes to avoid extra blank lines.
    """
    from wexample_filestate.helpers.flag import flag_exists

    # Preserve the entire leading_lines per node; additionally, capture the flag
    # comment lines from whichever node currently holds them so we can keep the flag
    # on the first node after sorting.
    original_leadings = [n.leading_lines for n in nodes]

    # Collect flag lines from any node (typically the first) to attach to new first
    def _flag_lines(ll: Sequence[cst.EmptyLine]) -> list[cst.EmptyLine]:
        return [
            el
            for el in ll
            if el.comment is not None and flag_exists(FLAG_NAME, el.comment.value)
        ]

    collected_flag_lines: list[cst.EmptyLine] = []
    for ll in original_leadings:
        fl = _flag_lines(ll)
        if fl:
            collected_flag_lines = fl
            break

    pairs: list[tuple[str, cst.SimpleStatementLine]] = []
    for node in nodes:
        name = _get_simple_assignment_name(node)
        if name is None:
            # Shouldn't happen given precondition
            continue
        pairs.append((name, node))

    # If already sorted, return original (no changes)
    sorted_pairs = sorted(pairs, key=lambda p: p[0].lower())
    if [n for _, n in sorted_pairs] == [n for _, n in pairs]:
        return nodes

    # Build new nodes preserving each node's original leading_lines, but move the
    # flag comment lines to the new first node (removing them from others).
    sorted_nodes: list[cst.SimpleStatementLine] = []

    # Capture blank lines that precede the flag comment from the first node
    first_node_blank_lines: list[cst.EmptyLine] = []
    if original_leadings:
        for el in original_leadings[0]:
            if el.comment is None:
                first_node_blank_lines.append(el)
            elif flag_exists(FLAG_NAME, el.comment.value):
                # Stop before the flag comment
                break

    # Pre-clean each node's leading_lines by removing any flag lines to avoid duplicates
    # and removing blank lines (except for the first node's leading blanks before flag)
    cleaned_leadings = []
    for idx_ll, ll in enumerate(original_leadings):
        cleaned = [
            el
            for el in ll
            if not (el.comment is not None and flag_exists(FLAG_NAME, el.comment.value))
            and el.comment is not None  # Remove blank lines (EmptyLine with no comment)
        ]
        cleaned_leadings.append(cleaned)

    for idx, (_, node) in enumerate(sorted_pairs):
        # Determine the original index of this node in 'nodes' list
        original_index = next((i for i, (_, n) in enumerate(pairs) if n is node), None)
        leading = (
            cleaned_leadings[original_index]
            if original_index is not None
            else node.leading_lines
        )

        # For the first node, add blank lines before flag, then flag lines
        if idx == 0:
            leading = first_node_blank_lines + collected_flag_lines + list(leading)

        sorted_nodes.append(node.with_changes(leading_lines=leading))
    return sorted_nodes


def _get_simple_assignment_name(stmt: cst.SimpleStatementLine) -> str | None:
    if len(stmt.body) != 1:
        return None
    small = stmt.body[0]
    if isinstance(small, cst.Assign):
        if len(small.targets) != 1:
            return None
        target = small.targets[0].target
        if isinstance(target, cst.Name) and _is_upper_name(target.value):
            return target.value
        return None
    if isinstance(small, cst.AnnAssign):
        target = small.target
        if isinstance(target, cst.Name) and _is_upper_name(target.value):
            return target.value
        return None
    return None


def _is_blank_line(stmt: cst.CSTNode) -> bool:
    # In Module.body, blank lines are represented as EmptyLine nodes
    return isinstance(stmt, cst.EmptyLine)


def _is_upper_name(name: str) -> bool:
    return name.isupper()


def _prev_line_has_flag(body_list: list[cst.CSTNode], index: int) -> bool:
    """Return True if the previous sibling is an EmptyLine whose comment contains the flag."""
    from wexample_filestate.helpers.flag import flag_exists

    if index - 1 < 0:
        return False
    prev = body_list[index - 1]
    if isinstance(prev, cst.EmptyLine) and prev.comment is not None:
        return flag_exists(FLAG_NAME, prev.comment.value)
    return False


def _stmt_has_flag(stmt: cst.SimpleStatementLine, src: str) -> bool:
    """Detect if a simple statement line is preceded by the filestate flag.

    We look into leading_lines comments, else fallback to searching raw src segment
    of the statement's leading trivia.
    """
    from wexample_filestate.helpers.flag import flag_exists

    # Check libcst leading_lines comments
    for el in stmt.leading_lines:
        if el.comment is not None:
            comment_text = el.comment.value  # includes '#'
            if flag_exists(FLAG_NAME, comment_text):
                return True
    # Do NOT fallback to scanning the entire file universally; detection via
    # previous sibling EmptyLine is handled by the callers.
    return False
