from __future__ import annotations

import libcst as cst


def find_main_guard_blocks(module: cst.Module) -> list[tuple[int, cst.If]]:
    """Return list of (index, IfNode) for all top-level __main__ guard blocks."""
    res: list[tuple[int, cst.If]] = []
    for i, stmt in enumerate(module.body):
        if is_main_guard_if(stmt):
            res.append((i, stmt))
    return res


def is_main_guard_at_end(module: cst.Module) -> bool:
    blocks = find_main_guard_blocks(module)
    if not blocks:
        return True
    last_index = blocks[-1][0]
    # Consider "at the end" if it's the last non-empty node (ignoring trailing blank lines)
    # Find last non-empty node index
    last_non_empty = -1
    for i in range(len(module.body) - 1, -1, -1):
        if not isinstance(module.body[i], cst.EmptyLine):
            last_non_empty = i
            break
    return last_index == last_non_empty


def is_main_guard_if(node: cst.CSTNode) -> bool:
    return isinstance(node, cst.If) and _is_name_eq_main(node.test)


def move_main_guard_to_end(module: cst.Module) -> cst.Module:
    blocks = find_main_guard_blocks(module)
    if not blocks:
        return module

    new_body = list(module.body)

    # Remove all blocks first (from highest index to lowest)
    removed: list[cst.If] = []
    for idx, node in sorted(blocks, key=lambda t: t[0], reverse=True):
        removed.append(new_body.pop(idx))
    removed.reverse()  # preserve original order

    # Strip leading_lines of the first moved guard only if it would create extra blank lines at end
    # In practice, we keep existing leading_lines to minimize diffs.
    # Append guards at the end (before trailing EmptyLines, if any)
    # Find insertion point: just before trailing EmptyLines
    insert_at = len(new_body)
    while insert_at > 0 and isinstance(new_body[insert_at - 1], cst.EmptyLine):
        insert_at -= 1

    for offset, node in enumerate(removed):
        new_body.insert(insert_at + offset, node)

    return module.with_changes(body=new_body)


def _is_name_eq_main(test: cst.BaseExpression) -> bool:
    # Match patterns: __name__ == "__main__" or '__main__'
    if not isinstance(test, cst.Comparison):
        return False
    # Expect a single comparator with Eq
    if len(test.comparisons) != 1:
        return False
    comp = test.comparisons[0]
    if not isinstance(comp.operator, cst.Equal):
        return False
    # Left should be Name("__name__") (optionally with parentheses tolerated by CST?)
    left_ok = isinstance(test.left, cst.Name) and test.left.value == "__name__"
    if not left_ok:
        return False
    # Right should be SimpleString of __main__
    right = comp.comparator
    if isinstance(right, cst.SimpleString):
        s = right.evaluated_value  # libcst provides unescaped python value
        return s == "__main__"
    return False
