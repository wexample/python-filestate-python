from __future__ import annotations

import libcst as cst

# Special attribute names and inner classes to prioritize
SPECIAL_ATTR_NAMES = {"__slots__", "__match_args__"}
SPECIAL_INNER_CLASS_NAMES = {"Config"}


def ensure_order_class_attributes_in_module(module: cst.Module) -> cst.Module:
    changed = False
    new_body = list(module.body)
    for idx, node in enumerate(new_body):
        if isinstance(node, cst.ClassDef):
            updated = reorder_class_attributes(node)
            if updated is not node:
                new_body[idx] = updated
                changed = True
    if not changed:
        return module
    return module.with_changes(body=new_body)


def find_attribute_blocks_in_class(
    classdef: cst.ClassDef,
) -> list[tuple[int, int, list[cst.CSTNode]]]:
    """Find contiguous blocks of class attributes within the class body.

    A block starts at an attribute statement and continues through subsequent
    attribute statements; it stops when hitting a blank separator (empty line without
    comment) or a non-attribute node (e.g., def, @decorated def, etc.).
    Inline and preceding comment lines are considered attached to the following node.

    Returns list of (start_index, end_index_exclusive, nodes)
    where indices refer to classdef.body.body positions.
    """
    body_list = list(classdef.body.body)
    n = len(body_list)
    blocks: list[tuple[int, int, list[cst.CSTNode]]] = []
    i = 0
    while i < n:
        node = body_list[i]
        if _is_attribute_statement(node):
            # Start a block
            j = i
            nodes: list[cst.CSTNode] = []
            while j < n:
                cur = body_list[j]
                if _is_attribute_statement(cur):
                    # If not the first, ensure there is no blank separator before cur
                    if j != i:
                        # Stop if there is a blank separator among leading_lines (for simple statements)
                        if isinstance(cur, cst.SimpleStatementLine):
                            if any(el.comment is None for el in cur.leading_lines):
                                break
                        # For ClassDef, presence of a preceding blank line is represented
                        # by a separate EmptyLine node; if previous sibling is a blank separator, stop.
                        prev = body_list[j - 1]
                        if _is_blank_separator(prev):
                            break
                    nodes.append(cur)
                    j += 1
                    continue
                # Stop on first non-attribute node
                break
            if nodes:
                blocks.append((i, j, nodes))
                i = j
                continue
        i += 1
    return blocks


def reorder_attribute_block(
    nodes: list[cst.CSTNode], *, dataclass_mode: bool = False
) -> list[cst.CSTNode]:
    """Reorder one attribute block by categories, preserving per-node leading comments.

    Order:
      1) Special (__slots__, __match_args__, inner class Config)
      2) Public A–Z
      3) Private/protected A–Z
    """

    def cat(node: cst.CSTNode) -> tuple:
        name = _attr_name(node) or ""
        if _is_special_attribute(node):
            # Category 0: special always first
            return (0, _sort_key(name), False)
        if dataclass_mode:
            # In dataclass mode, prioritize fields without defaults (required),
            # then fields with defaults/default_factory; non-field attributes come after.
            if _is_dataclass_field(node):
                if _dataclass_field_has_default(node):
                    # Category 2: defaulted fields
                    return (2, _sort_key(name), False)
                # Category 1: required fields
                return (1, _sort_key(name), False)
            # Non-field attributes: keep public before private after fields
            if _is_public(name):
                return (3, _sort_key(name), False)
            return (4, _sort_key(name), False)
        # Default (non-dataclass) ordering: public, then private
        if _is_public(name):
            # Category 1
            return (1, _sort_key(name), False)
        # Category 2 (private/protected)
        return (2, _sort_key(name), False)

    original = list(nodes)
    sorted_nodes = sorted(nodes, key=cat)

    # If unchanged order, return original to avoid diffs
    if sorted_nodes == original:
        return original

    # Normalize leading_lines: only the first node keeps its leading_lines,
    # others should have minimal leading_lines (preserve comments but remove blank lines).
    out: list[cst.CSTNode] = []
    for idx, node in enumerate(sorted_nodes):
        if idx == 0:
            # First node: keep its leading_lines as-is
            out.append(node)
        else:
            # Subsequent nodes: strip blank leading_lines, keep only comment lines
            if isinstance(node, cst.SimpleStatementLine):
                # Filter leading_lines to keep only comment lines
                comment_lines = [
                    line for line in node.leading_lines if line.comment is not None
                ]
                out.append(node.with_changes(leading_lines=comment_lines))
            else:
                # For ClassDef or other nodes, just append as-is
                # (blank separators are handled by EmptyLine nodes between body items)
                out.append(node)
    return out


def reorder_class_attributes(classdef: cst.ClassDef) -> cst.ClassDef:
    blocks = find_attribute_blocks_in_class(classdef)
    if not blocks:
        return classdef

    changed = False
    body_list = list(classdef.body.body)
    dc_mode = _is_dataclass(classdef)
    for start, end, nodes in reversed(blocks):
        new_nodes = reorder_attribute_block(nodes, dataclass_mode=dc_mode)
        if new_nodes != nodes:
            body_list[start:end] = new_nodes
            changed = True
    if not changed:
        return classdef
    return classdef.with_changes(body=classdef.body.with_changes(body=body_list))


def _attr_name(node: cst.CSTNode) -> str | None:
    if isinstance(node, cst.SimpleStatementLine) and len(node.body) == 1:
        small = node.body[0]
        if isinstance(small, cst.Assign):
            tgt = small.targets[0].target
            if isinstance(tgt, cst.Name):
                return tgt.value
        if isinstance(small, cst.AnnAssign):
            tgt = small.target
            if isinstance(tgt, cst.Name):
                return tgt.value
    if isinstance(node, cst.ClassDef):
        return node.name.value
    return None


def _dataclass_field_has_default(node: cst.CSTNode) -> bool:
    """Return True if the dataclass field has a default value or default_factory.

    We treat any AnnAssign with a non-None value as having a default.
    This includes calls like field(default=..., default_factory=...).
    """
    if not _is_dataclass_field(node):
        return False
    assert isinstance(node, cst.SimpleStatementLine)
    small = node.body[0]
    assert isinstance(small, cst.AnnAssign)
    return small.value is not None


def _is_attribute_statement(node: cst.CSTNode) -> bool:
    """Return True if node is a class-level attribute we should order.

    We consider:
      - Simple single-target Name assignments (Assign/AnnAssign) whose target name is NOT UPPER_CASE
      - Inner class definitions (e.g., Config) as attributes for ordering

    Uppercase names are ignored here (treated as constants in another operation).
    """
    if isinstance(node, cst.SimpleStatementLine) and len(node.body) == 1:
        small = node.body[0]
        if isinstance(small, cst.Assign):
            # Only simple single-target Name assignments
            if len(small.targets) != 1:
                return False
            target = small.targets[0].target
            if isinstance(target, cst.Name):
                # Ignore UPPER_CASE constants
                if target.value.isupper():
                    return False
                return True
            return False
        if isinstance(small, cst.AnnAssign):
            target = small.target
            if isinstance(target, cst.Name):
                if target.value.isupper():
                    return False
                return True
            return False
    # Pydantic / config style inner classes are considered attributes for ordering
    if isinstance(node, cst.ClassDef) and isinstance(node.name, cst.Name):
        return True
    return False


def _is_blank_separator(node: cst.CSTNode) -> bool:
    # A blank separator is an EmptyLine without a comment
    return isinstance(node, cst.EmptyLine) and node.comment is None


def _is_comment_line(node: cst.CSTNode) -> bool:
    return isinstance(node, cst.EmptyLine) and node.comment is not None


def _is_dataclass(classdef: cst.ClassDef) -> bool:
    """Detect if class has a @dataclass decorator (dataclass or dataclasses.dataclass)."""
    for dec in classdef.decorators:
        try:
            expr = dec.decorator
            if isinstance(expr, cst.Name) and expr.value == "dataclass":
                return True
            if isinstance(expr, cst.Attribute) and isinstance(expr.attr, cst.Name):
                if expr.attr.value == "dataclass":
                    return True
        except Exception:
            continue
    return False


def _is_dataclass_field(node: cst.CSTNode) -> bool:
    """Dataclass fields are typically annotated assignments (AnnAssign) with non-UPPER names."""
    if isinstance(node, cst.SimpleStatementLine) and len(node.body) == 1:
        small = node.body[0]
        if isinstance(small, cst.AnnAssign):
            tgt = small.target
            if isinstance(tgt, cst.Name) and not tgt.value.isupper():
                return True
    return False


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _is_special_attribute(node: cst.CSTNode) -> bool:
    name = _attr_name(node)
    if name is None:
        return False
    if name in SPECIAL_ATTR_NAMES:
        return True
    if isinstance(node, cst.ClassDef) and name in SPECIAL_INNER_CLASS_NAMES:
        return True
    return False


def _sort_key(name: str) -> tuple:
    # Case-insensitive A-Z; ensure '_' sorts after letters
    # We achieve this by key: (name without leading '_', is_private)
    return (name.lstrip("_").lower(), name.startswith("_"))
