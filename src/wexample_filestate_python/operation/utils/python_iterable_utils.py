from __future__ import annotations

FLAG_NAME = "python-iterable-sort"


def reorder_flagged_iterables(src: str) -> str:
    """Sort items of flagged iterable blocks (typically list literals) alphabetically.

    - Looks for lines with '# filestate: python-iterable-sort'.
    - Sorts the contiguous following element lines until a blank line or closing bracket.
    - Preserves comments: a contiguous block of comment lines is attached to the
      item immediately below it and moves with that item.
    - Preserves indentation and commas; compares using a case-insensitive key on
      the item line's stripped content.
    - If already sorted, returns original src unchanged.
    """
    lines = src.splitlines()
    if not lines:
        return src

    flag_lines = _find_flag_line_indices(src)
    if not flag_lines:
        return src

    changed = False

    def split_into_groups(block_lines: list[str]) -> list[list[str]]:
        groups: list[list[str]] = []
        pending_comments: list[str] = []
        for ln in block_lines:
            if ln.lstrip().startswith("#"):
                pending_comments.append(ln)
                continue
            # item line
            group = pending_comments + [ln]
            groups.append(group)
            pending_comments = []
        # Any trailing comments without item are ignored for sorting and left in place
        # (shouldn't occur in expected usage). If present, attach to last group to preserve.
        if pending_comments:
            if groups:
                groups[-1].extend(pending_comments)
            else:
                groups.append(pending_comments)
        return groups

    def group_key(g: list[str]) -> str:
        # Use the first non-comment line in group as key
        for ln in g:
            if not ln.lstrip().startswith("#"):
                # Remove trailing comma for comparison but don't modify actual text
                item = ln.strip()
                if item.endswith(","):
                    item = item[:-1]
                return item.lower()
        return ""  # fallback

    for flag_idx in reversed(flag_lines):
        start, end = _collect_iterable_block(lines, flag_idx)
        if start >= end:
            continue
        block = lines[start:end]

        groups = split_into_groups(block)
        # Build current order keys for no-op detection
        current_keys = [group_key(g) for g in groups]
        sorted_groups = sorted(groups, key=group_key)
        sorted_keys = [group_key(g) for g in sorted_groups]

        if sorted_keys == current_keys:
            continue

        # Flatten groups back to lines
        new_block: list[str] = []
        for g in sorted_groups:
            new_block.extend(g)

        lines[start:end] = new_block
        changed = True

    return "\n".join(lines) if changed else src


def _collect_iterable_block(lines: list[str], flag_idx: int) -> tuple[int, int]:
    """Given the index of the flag line, collect the contiguous item block range.

    Returns (start_idx, end_idx_exclusive) of lines to sort. We start at the next
    non-empty, non-comment line after the flag, and stop before the first blank
    line or the closing bracket ']' at the same or lesser indentation level.
    """
    n = len(lines)
    # Determine base indentation from the flag line
    flag_line = lines[flag_idx]
    base_indent = len(flag_line) - len(flag_line.lstrip(" \t"))

    # Start scanning after the flag line
    i = flag_idx + 1
    # Skip immediate blank/comment lines (though the example shows none)
    while i < n and (lines[i].strip() == "" or lines[i].lstrip().startswith("#")):
        i += 1
    start = i

    # Scan until blank line or closing bracket ']' at indentation <= base
    while i < n:
        stripped = lines[i].strip()
        # Stop at blank separator line
        if stripped == "":
            break
        # Stop when list ends
        curr_indent = len(lines[i]) - len(lines[i].lstrip(" \t"))
        if stripped.startswith("]") and curr_indent <= base_indent:
            break
        # Stop if we encounter a trailing comment-only line
        if lines[i].lstrip().startswith("#"):
            break
        i += 1

    end = i
    return start, end


def _find_flag_line_indices(src: str) -> list[int]:
    """Return line indices where the iterable sort flag appears."""
    from wexample_filestate.helpers.flag import flag_exists

    lines = src.splitlines()
    indices: list[int] = []
    for i, line in enumerate(lines):
        if flag_exists(FLAG_NAME, line):
            indices.append(i)
    return indices
