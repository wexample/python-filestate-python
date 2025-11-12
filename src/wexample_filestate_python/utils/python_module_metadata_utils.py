from __future__ import annotations

import libcst as cst

# Common, recognized module metadata names
METADATA_NAMES: tuple[str, ...] = (
    "__all__",
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__copyright__",
    "__title__",
    "__description__",
)


def find_module_metadata_statements(
    module: cst.Module,
) -> list[tuple[int, cst.SimpleStatementLine, str]]:
    """Find all module-level metadata assignments.

    Returns list of tuples: (index_in_body, node, metadata_name)
    """
    results: list[tuple[int, cst.SimpleStatementLine, str]] = []
    for i, stmt in enumerate(module.body):
        name = _get_assignment_target_name(stmt)
        if name is not None:
            assert isinstance(stmt, cst.SimpleStatementLine)
            results.append((i, stmt, name))
    return results


def group_and_sort_module_metadata(module: cst.Module) -> cst.Module:
    """Group and sort module metadata assignments by variable name (A–Z).

    - Collect all recognized metadata assignments at module level
    - Remove them from their current positions
    - Sort them case-insensitively by the metadata name
    - Insert them as a contiguous block at the target index
    - Avoid introducing extra blank lines by clearing leading_lines
    """
    found = find_module_metadata_statements(module)
    if not found:
        return module

    # Determine insertion index before we mutate the body
    insert_at = target_index_for_module_metadata(module)

    # Remove from body (reverse order) and collect nodes with cleaned leading lines
    to_remove_indices = sorted([i for i, _, _ in found], reverse=True)
    new_body: list[cst.CSTNode] = list(module.body)
    moved: list[tuple[str, cst.SimpleStatementLine]] = []

    for idx in to_remove_indices:
        node = new_body.pop(idx)
        assert isinstance(node, cst.SimpleStatementLine)
        name = _get_assignment_target_name(node)
        if name is None:
            # Should not happen; skip
            continue
        moved.append((name, node.with_changes(leading_lines=[])))

    # Sort moved by name case-insensitively, '_' after letters rule not needed here
    moved.sort(key=lambda t: t[0].lower())

    # Adjust insertion index after removals that occurred before it
    num_removed_before = sum(1 for idx in to_remove_indices if idx < insert_at)
    adjusted_insert = insert_at - num_removed_before

    # Insert in order
    for offset, (_, node) in enumerate(moved):
        new_body.insert(adjusted_insert + offset, node)

    return module.with_changes(body=new_body)


def target_index_for_module_metadata(module: cst.Module) -> int:
    """Compute target index to insert grouped module metadata.

    According to file-level ordering:
    - after imports
    - after TYPE_CHECKING block
    - then module metadata

    So we insert after the last TYPE_CHECKING block if present, else after last regular
    import if present, else after last __future__ import, else after docstring, else 0.
    """
    from wexample_filestate_python.utils.python_type_checking_utils import (
        _is_future_import,
        _is_regular_import,
        find_type_checking_blocks,
    )

    last_type_checking = -1
    for idx, _if in find_type_checking_blocks(module):
        last_type_checking = max(last_type_checking, idx)

    last_regular_import = -1
    last_future_import = -1
    for i, stmt in enumerate(module.body):
        if _is_regular_import(stmt):
            last_regular_import = i
        elif _is_future_import(stmt):
            last_future_import = i

    if last_type_checking != -1:
        return last_type_checking + 1
    if last_regular_import != -1:
        return last_regular_import + 1
    if last_future_import != -1:
        return last_future_import + 1
    if module.has_docstring:
        return 1
    return 0


def _get_assignment_target_name(stmt: cst.CSTNode) -> str | None:
    """Return the variable name if this statement is an assignment to a metadata name.

    Only supports simple module-level assignments like `__version__ = ...` or
    annotated assignment `__version__: str = ...`. Ignores destructuring or multiple targets.
    """
    if not isinstance(stmt, cst.SimpleStatementLine):
        return None

    if len(stmt.body) != 1:
        return None

    small = stmt.body[0]

    if isinstance(small, cst.Assign):
        # Only allow single target
        if len(small.targets) != 1:
            return None
        target = small.targets[0].target
        if isinstance(target, cst.Name) and target.value in METADATA_NAMES:
            return target.value
        return None

    if isinstance(small, cst.AnnAssign):
        target = small.target
        if isinstance(target, cst.Name) and target.value in METADATA_NAMES:
            return target.value
        return None

    return None
