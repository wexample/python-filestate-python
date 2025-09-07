from __future__ import annotations

from typing import List, Optional, Tuple

import libcst as cst


def collect_module_classes(module: cst.Module) -> List[Tuple[int, cst.ClassDef]]:
    """Collect top-level classes with their indices in the module body."""
    classes: List[Tuple[int, cst.ClassDef]] = []
    for idx, node in enumerate(module.body):
        if isinstance(node, cst.ClassDef):
            classes.append((idx, node))
    return classes


def _is_main_guard(node: cst.CSTNode) -> bool:
    if not isinstance(node, cst.If):
        return False
    test = node.test
    if isinstance(test, cst.Comparison):
        left = test.left
        comps = test.comparisons
        if len(comps) == 1 and isinstance(left, cst.Name) and left.value == "__name__":
            comp = comps[0]
            if isinstance(comp.operator, cst.Equal):
                right = comp.comparator
                if isinstance(right, cst.SimpleString):
                    val = right.evaluated_value if hasattr(right, "evaluated_value") else right.value.strip("\"'")
                    return val == "__main__" or right.value.strip() in ("'__main__'", '"__main__"')
    return False


def reorder_module_classes(module: cst.Module) -> cst.Module:
    """Reorder module-level classes alphabetically (case-insensitive) using an anchor strategy.

    - Determine the anchor as the index of the first class in the original module.
    - Remove all classes from the body, sort them by name (A–Z), and reinsert
      them as a contiguous block at the anchor position (adjusted for removals).
    - Keep the __main__ guard last (never insert after it).
    - Preserve leading_lines of each class; do not alter spacing within each class.
    """
    classes_with_idx = collect_module_classes(module)
    if not classes_with_idx:
        return module

    # Extract in original order and compute sorted order
    classes = [cls for _, cls in classes_with_idx]
    sorted_classes = sorted(classes, key=lambda c: c.name.value.lower())

    # If already sorted in place, still ensure they are contiguous at original positions? We'll rebuild and compare code.
    remove_indices = sorted(idx for idx, _ in classes_with_idx)

    new_body: List[cst.CSTNode] = []
    for idx, node in enumerate(module.body):
        if idx in remove_indices:
            continue
        new_body.append(node)

    # Anchor = index of first class in original body
    first_class_index = classes_with_idx[0][0]
    removed_before_anchor = sum(1 for i in remove_indices if i < first_class_index)
    insert_at = first_class_index - removed_before_anchor

    # Keep __main__ guard last
    for idx, node in enumerate(new_body):
        if _is_main_guard(node) and insert_at > idx:
            insert_at = idx
            break

    # Reinsert classes
    new_body[insert_at:insert_at] = [cls for cls in sorted_classes]

    return module.with_changes(body=new_body)
