from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import libcst as cst

from wexample_filestate.helpers.flag import flag_exists

FLAG_NAME = "python-constant-sort"


def _stmt_has_flag(stmt: cst.SimpleStatementLine, src: str) -> bool:
    """Detect if a simple statement line is preceded by the filestate flag.

    We look into leading_lines comments, else fallback to searching raw src segment
    of the statement's leading trivia.
    """
    # Check libcst leading_lines comments
    for el in stmt.leading_lines:
        if el.comment is not None:
            comment_text = el.comment.value  # includes '#'
            if flag_exists(FLAG_NAME, comment_text):
                return True
    # Do NOT fallback to scanning the entire file; only consider an inline flag
    # directly attached to this statement via leading_lines.
    return False


def _is_upper_name(name: str) -> bool:
    return name.isupper()


def _get_simple_assignment_name(stmt: cst.SimpleStatementLine) -> Optional[str]:
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


def find_flagged_constant_blocks(module: cst.Module, src: str) -> List[Tuple[int, int, List[cst.SimpleStatementLine]]]:
    """Find blocks of contiguous UPPER_CASE assignments following the filestate flag.

    A block starts at the first assignment statement that has the flag in its leading
    comments; it continues with subsequent contiguous constant assignments until a
    blank line or a non-constant statement is found.

    Returns list of tuples (start_index, end_index_exclusive, nodes_in_block)
    where indices refer to module.body positions.
    """
    blocks: List[Tuple[int, int, List[cst.SimpleStatementLine]]] = []

    i = 0
    body = module.body
    n = len(body)
    while i < n:
        stmt = body[i]
        if isinstance(stmt, cst.SimpleStatementLine):
            if _stmt_has_flag(stmt, src) and _get_simple_assignment_name(stmt) is not None:
                # Start a block at i
                j = i
                nodes: List[cst.SimpleStatementLine] = []
                while j < n:
                    s = body[j]
                    if isinstance(s, cst.SimpleStatementLine):
                        name = _get_simple_assignment_name(s)
                        if name is None:
                            break
                        nodes.append(s)
                        j += 1
                        continue
                    # Stop at blank line or any other node
                    break
                if nodes:
                    blocks.append((i, j, nodes))
                    i = j
                    continue
        i += 1

    return blocks


def sort_constants_block(nodes: List[cst.SimpleStatementLine]) -> List[cst.SimpleStatementLine]:
    """Return a new list of nodes sorted by variable name (case-insensitive).

    Preserve the flag comment by attaching it to the first node of the
    sorted block (even if a different node becomes first after sorting),
    and clear leading_lines of subsequent nodes to avoid extra blank lines.
    """
    # Preserve the entire leading_lines of the original first node in the block
    # (this includes blank lines and the flag comment), so spacing is not lost.
    original_first_leading = nodes[0].leading_lines

    pairs: List[Tuple[str, cst.SimpleStatementLine]] = []
    for node in nodes:
        name = _get_simple_assignment_name(node)
        if name is None:
            # Shouldn't happen given precondition
            continue
        pairs.append((name, node))

    # If already sorted, return original
    sorted_pairs = sorted(pairs, key=lambda p: p[0].lower())
    if [n for _, n in sorted_pairs] == [n for _, n in pairs]:
        # Ensure the leading_lines (including flag and preceding blank line) remain attached
        first = nodes[0]
        if first.leading_lines != original_first_leading:
            nodes = [first.with_changes(leading_lines=original_first_leading)] + [
                n if idx == 0 else n for idx, n in enumerate(nodes[1:], start=1)
            ]
        return nodes

    # Helper to filter out only the flag comment from a node's leading_lines,
    # keeping any other comments intact.
    def _strip_flag_from_leading(node: cst.SimpleStatementLine) -> cst.SimpleStatementLine:
        if not node.leading_lines:
            return node
        new_leading: List[cst.EmptyLine] = []
        for el in node.leading_lines:
            if el.comment is not None and flag_exists(FLAG_NAME, el.comment.value):
                # drop the flag line for non-first nodes
                continue
            new_leading.append(el)
        return node.with_changes(leading_lines=new_leading)

    sorted_nodes: List[cst.SimpleStatementLine] = []
    for idx, (_, node) in enumerate(sorted_pairs):
        if idx == 0:
            # Attach the full original leading_lines (preserving spacing and flag)
            sorted_nodes.append(node.with_changes(leading_lines=original_first_leading))
        else:
            sorted_nodes.append(_strip_flag_from_leading(node))
    return sorted_nodes


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
