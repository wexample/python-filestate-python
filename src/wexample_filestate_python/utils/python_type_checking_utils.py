from __future__ import annotations

import libcst as cst


def find_type_checking_blocks(module: cst.Module) -> list[tuple[int, cst.If]]:
    """Return list of (index, IfNode) for all top-level `if TYPE_CHECKING:` blocks."""
    results: list[tuple[int, cst.If]] = []
    for i, stmt in enumerate(module.body):
        if isinstance(stmt, cst.If) and _is_type_checking_test(stmt.test):
            results.append((i, stmt))
    return results


def move_type_checking_blocks_after_imports(module: cst.Module) -> cst.Module:
    """Move all `if TYPE_CHECKING:` blocks to just after regular imports.
    Preserves the order of the blocks and removes extra leading blank lines.
    """
    blocks = find_type_checking_blocks(module)
    if not blocks:
        return module

    # Determine target position before removal to avoid index shifts
    insert_at = target_index_for_type_checking(module)

    # Remove blocks from body (from highest index to lowest to keep indices valid)
    remove_indices = sorted((i for i, _ in blocks), reverse=True)
    new_body = list(module.body)
    moved_blocks: list[cst.If] = []
    for idx in remove_indices:
        node = new_body.pop(idx)
        assert isinstance(node, cst.If)
        # Strip leading lines to avoid introducing blank lines
        moved_blocks.append(node.with_changes(leading_lines=[]))

    # We removed in reverse; preserve original relative order by reversing back
    moved_blocks.reverse()

    # Adjust insert_at for prior removals that occurred before it
    num_removed_before = sum(1 for idx in remove_indices if idx < insert_at)
    adjusted_insert = insert_at - num_removed_before

    for offset, block in enumerate(moved_blocks):
        new_body.insert(adjusted_insert + offset, block)

    return module.with_changes(body=new_body)


def target_index_for_type_checking(module: cst.Module) -> int:
    """Compute target insertion index for TYPE_CHECKING blocks.
    After last regular import if any; otherwise after last __future__ import;
    otherwise after module docstring if present; else position 0.
    """
    last_regular_import = -1
    last_future_import = -1

    for i, stmt in enumerate(module.body):
        if _is_regular_import(stmt):
            last_regular_import = i
        elif _is_future_import(stmt):
            last_future_import = i
        else:
            # stop scanning when hitting first non-import after having passed imports?
            # We still record all to get the last occurrence.
            pass

    if last_regular_import != -1:
        return last_regular_import + 1
    if last_future_import != -1:
        return last_future_import + 1

    # Module docstring at index 0?
    if module.has_docstring:
        return 1

    return 0


def _is_future_import(stmt: cst.CSTNode) -> bool:
    if isinstance(stmt, cst.SimpleStatementLine):
        for small in stmt.body:
            if isinstance(small, cst.ImportFrom):
                # from __future__ import ...
                mod = small.module
                if isinstance(mod, cst.Name) and mod.value == "__future__":
                    return True
    return False


def _is_regular_import(stmt: cst.CSTNode) -> bool:
    if isinstance(stmt, cst.SimpleStatementLine):
        for small in stmt.body:
            if isinstance(small, (cst.Import, cst.ImportFrom)):
                # Exclude __future__
                if isinstance(small, cst.ImportFrom):
                    mod = small.module
                    if isinstance(mod, cst.Name) and mod.value == "__future__":
                        return False
                return True
    return False


def _is_type_checking_test(test: cst.BaseExpression) -> bool:
    # TYPE_CHECKING
    if isinstance(test, cst.Name) and test.value == "TYPE_CHECKING":
        return True
    # typing.TYPE_CHECKING
    if isinstance(test, cst.Attribute):
        if isinstance(test.attr, cst.Name) and test.attr.value == "TYPE_CHECKING":
            # Optional: enforce base name 'typing'
            if isinstance(test.value, cst.Name) and test.value.value == "typing":
                return True
    return False
