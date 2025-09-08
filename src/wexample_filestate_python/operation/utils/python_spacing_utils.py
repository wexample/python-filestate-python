from __future__ import annotations

from typing import List, Optional, Tuple

import libcst as cst

# Reuse property detection from methods utils
try:
    from wexample_filestate_python.operation.utils.python_class_methods_utils import (
        _property_kind,
    )
except Exception:  # pragma: no cover - fallback if import graph changes
    def _property_kind(func: cst.FunctionDef) -> tuple[Optional[str], Optional[str]]:
        return None, None


def _is_comment_emptyline(node: cst.CSTNode) -> bool:
    return isinstance(node, cst.EmptyLine) and node.comment is not None


def _is_blank_emptyline(node: cst.CSTNode) -> bool:
    return isinstance(node, cst.EmptyLine) and node.comment is None


def _trim_blank_emptylines(seq: List[cst.CSTNode]) -> List[cst.CSTNode]:
    return [n for n in seq if not _is_blank_emptyline(n)]


def _count_blank_between(seq: List[cst.CSTNode], start_idx: int, end_idx: int) -> int:
    count = 0
    for i in range(start_idx + 1, end_idx):
        if _is_blank_emptyline(seq[i]):
            count += 1
    return count


def _set_blank_between(seq: List[cst.CSTNode], start_idx: int, end_idx: int, desired: int) -> List[cst.CSTNode]:
    """Return new list where the number of blank EmptyLine nodes between start and end is set to desired.
    Comment EmptyLines are preserved and not counted.
    """
    # Collect indices for removal (blank lines only)
    new_seq = list(seq)
    # First remove all blank lines in (start_idx, end_idx)
    removes = []
    for i in range(start_idx + 1, end_idx):
        if _is_blank_emptyline(new_seq[i]):
            removes.append(i)
    for i in reversed(removes):
        new_seq.pop(i)
    # Recompute insertion position: after start_idx, before (adjusted) end
    insert_pos = start_idx + 1
    # Insert desired number of blank lines, but keep any comment EmptyLines already present
    for _ in range(desired):
        new_seq.insert(insert_pos, cst.EmptyLine())
        insert_pos += 1
    return new_seq


def _cap_blank_between(seq: List[cst.CSTNode], start_idx: int, end_idx: int, max_allowed: int) -> List[cst.CSTNode]:
    """Trim blank EmptyLines between start and end to at most max_allowed; never add new blanks.
    Comment EmptyLines are preserved.
    """
    current = _count_blank_between(seq, start_idx, end_idx)
    if current <= max_allowed:
        return seq
    # Remove (current - max_allowed) blank lines closest to end_idx
    to_remove = current - max_allowed
    new_seq = list(seq)
    # Iterate backwards to remove later blanks first
    i = end_idx - 1
    while i > start_idx and to_remove > 0:
        if _is_blank_emptyline(new_seq[i]):
            new_seq.pop(i)
            to_remove -= 1
            end_idx -= 1
        i -= 1
    return new_seq


def _ensure_blank_after(seq: List[cst.CSTNode], idx: int, desired: int) -> List[cst.CSTNode]:
    # Find next non-comment node index after idx
    j = idx + 1
    while j < len(seq) and _is_comment_emptyline(seq[j]):
        j += 1
    if j >= len(seq):
        return seq
    current = _count_blank_between(seq, idx, j)
    if current == desired:
        return seq
    return _set_blank_between(seq, idx, j, desired)


def _ensure_blank_before(seq: List[cst.CSTNode], idx: int, desired: int) -> List[cst.CSTNode]:
    """Ensure there are desired visual separation lines before idx.

    Visual separation lines are the contiguous sequence of EmptyLine nodes immediately
    preceding idx (both blank and comment EmptyLines). We apply conservative rules:
    - If there are any comment EmptyLines in that contiguous run, we do NOT insert or
      remove additional blank lines (we assume comments serve as separation).
    - Otherwise, we adjust the number of blank EmptyLines to match desired.
    """
    # Scan contiguous EmptyLines immediately before idx
    j = idx - 1
    blank_count = 0
    comment_count = 0
    while j >= 0 and isinstance(seq[j], cst.EmptyLine):
        if seq[j].comment is None:
            blank_count += 1
        else:
            comment_count += 1
        j -= 1

    # If comments present in separation, don't touch spacing
    if comment_count > 0:
        return seq

    # No comments in separation; j now points to previous non-emptyline node (or -1)
    prev_index = j
    if prev_index < 0:
        # Beginning; normalize leading blanks to desired
        new_seq = list(seq)
        # Remove all leading blanks
        k = 0
        while k < len(new_seq) and _is_blank_emptyline(new_seq[k]):
            new_seq.pop(k)
        # Insert desired blanks at front
        for _ in range(desired):
            new_seq.insert(0, cst.EmptyLine())
        return new_seq

    # Current blank separation equals blank_count; adjust to desired
    if blank_count == desired:
        return seq

    # We need to set blank lines between prev_index and idx to desired
    return _set_blank_between(seq, prev_index, idx, desired)


from wexample_filestate_python.operation.utils.python_docstring_utils import (
    find_module_docstring,
)


def normalize_module_spacing(module: cst.Module) -> cst.Module:
    body = list(module.body)
    changed = False

    # 1) 1 blank line after module docstring (if present) — cap only, do not add
    ds_node, ds_idx = find_module_docstring(module)
    if ds_node is not None and len(body) > ds_idx + 1:
        # Cap blanks to at most 1
        # Find next non-comment node index
        j = ds_idx + 1
        while j < len(body) and _is_comment_emptyline(body[j]):
            j += 1
        if j < len(body):
            new_body = _cap_blank_between(body, ds_idx, j, 1)
        else:
            new_body = body
        if new_body is not body:
            body = new_body
            changed = True

    # 2) 1 blank line after TYPE_CHECKING blocks (top-level) — cap only
    for idx, stmt in enumerate(body):
        if isinstance(stmt, cst.If):
            # if TYPE_CHECKING
            test = stmt.test
            if isinstance(test, cst.Name) and test.value == "TYPE_CHECKING":
                # Cap to at most 1
                # Find next non-comment node index
                j = idx + 1
                while j < len(body) and _is_comment_emptyline(body[j]):
                    j += 1
                if j < len(body):
                    new_body = _cap_blank_between(body, idx, j, 1)
                else:
                    new_body = body
                if new_body is not body:
                    body = new_body
                    changed = True

    # 3) Ensure at most 2 blank lines before top-level classes and functions (do not add)
    for idx, stmt in enumerate(body):
        if isinstance(stmt, (cst.ClassDef, cst.FunctionDef)):
            # Don't enforce before the first statement in the file
            if idx == 0:
                continue
            # Cap only: count current blanks/comments before; if comments present, skip; else cap blanks to 2
            # Determine previous non-emptyline index
            j = idx - 1
            has_comment = False
            while j >= 0 and isinstance(body[j], cst.EmptyLine):
                if body[j].comment is not None:
                    has_comment = True
                j -= 1
            if not has_comment and j >= 0:
                new_body = _cap_blank_between(body, j, idx, 2)
            else:
                new_body = body
            if new_body is not body:
                body = new_body
                changed = True

    return module if not changed else module.with_changes(body=body)


def _ensure_one_blank_after_docstring_in_suite(suite: cst.IndentedBlock) -> cst.IndentedBlock:
    body = list(suite.body)
    if not body:
        return suite
    # Detect docstring at first statement
    first = body[0]
    if not (
        isinstance(first, cst.SimpleStatementLine)
        and len(first.body) == 1
        and isinstance(first.body[0], cst.Expr)
        and isinstance(first.body[0].value, cst.SimpleString)
    ):
        # Non-docstring start: remove any leading blank EmptyLines (non-expansive)
        k = 0
        changed = False
        while k < len(body) and _is_blank_emptyline(body[k]):
            body.pop(k)
            changed = True
        return suite if not changed else suite.with_changes(body=body)

    # Docstring present: cap blanks after it to at most 1; never insert if 0.
    # Find next non-comment node after docstring
    j = 1
    while j < len(body) and _is_comment_emptyline(body[j]):
        j += 1
    if j >= len(body):
        return suite
    current = _count_blank_between(body, 0, j)
    # If there are comment EmptyLines immediately after docstring, treat as separator; don't add blanks
    # Already handled by counting only blank EmptyLines; if current == 0, do nothing
    if current <= 1:
        return suite
    new_body = _cap_blank_between(body, 0, j, 1)
    return suite.with_changes(body=new_body)


def _is_property_method(func: cst.FunctionDef) -> bool:
    base, kind = _property_kind(func)
    return base is not None


def normalize_class_spacing(classdef: cst.ClassDef) -> cst.ClassDef:
    changed = False
    body = list(classdef.body.body)

    # 1) At most 1 blank line after class docstring (do not add)
    if body:
        first = body[0]
        if (
            isinstance(first, cst.SimpleStatementLine)
            and len(first.body) == 1
            and isinstance(first.body[0], cst.Expr)
            and isinstance(first.body[0].value, cst.SimpleString)
        ):
            # Cap only
            j = 1
            while j < len(body) and _is_comment_emptyline(body[j]):
                j += 1
            if j < len(body):
                new_body = _cap_blank_between(body, 0, j, 1)
            else:
                new_body = body
            if new_body is not body:
                body = new_body
                changed = True

    # 2) 1 blank line between class methods; 0 between consecutive property group members
    # Walk through body and normalize blanks between consecutive FunctionDef nodes
    i = 0
    while i < len(body) - 1:
        cur = body[i]
        j = i + 1
        # skip comment empty lines when determining adjacency target
        while j < len(body) and _is_comment_emptyline(body[j]):
            j += 1
        if j >= len(body):
            break
        nxt = body[j]
        if isinstance(cur, cst.FunctionDef) and isinstance(nxt, cst.FunctionDef):
            # Determine max blanks
            max_allowed = 1
            if _is_property_method(cur) and _is_property_method(nxt):
                max_allowed = 0
            # If there are comment EmptyLines between the two methods, do not add blanks; only trim
            has_comment_between = any(
                isinstance(body[k], cst.EmptyLine) and body[k].comment is not None
                for k in range(i + 1, j)
            )
            if has_comment_between:
                max_allowed = 0
            new_body = _cap_blank_between(body, i, j, max_allowed)
            if new_body is not body:
                body = new_body
                changed = True
            i = j
            continue
        i += 1

    # 3) Normalize function/method suites: cap to at most 1 blank after docstring; remove leading blanks otherwise
    new_body2 = list(body)
    for idx, node in enumerate(new_body2):
        if isinstance(node, cst.FunctionDef) and isinstance(node.body, cst.IndentedBlock):
            new_suite = _ensure_one_blank_after_docstring_in_suite(node.body)
            if new_suite is not node.body:
                new_body2[idx] = node.with_changes(body=new_suite)
                changed = True

    return classdef if not changed else classdef.with_changes(body=classdef.body.with_changes(body=new_body2))


def normalize_spacing_everywhere(module: cst.Module) -> cst.Module:
    # Module-level rules
    mod = normalize_module_spacing(module)

    # Class-level rules for each class
    new_body = list(mod.body)
    changed = False
    for idx, node in enumerate(new_body):
        if isinstance(node, cst.ClassDef):
            new_node = normalize_class_spacing(node)
            if new_node is not node:
                new_body[idx] = new_node
                changed = True
        if isinstance(node, cst.FunctionDef) and isinstance(node.body, cst.IndentedBlock):
            # Function-level: normalize suite blank after docstring and no initial blank
            new_suite = _ensure_one_blank_after_docstring_in_suite(node.body)
            if new_suite is not node.body:
                new_body[idx] = node.with_changes(body=new_suite)
                changed = True

    return mod if not changed else mod.with_changes(body=new_body)
