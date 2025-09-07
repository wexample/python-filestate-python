from __future__ import annotations

import re
from typing import List, Tuple

from wexample_filestate.helpers.flag import flag_exists

FLAG_NAME = "python-iterable-sort"


def _find_flag_line_indices(src: str) -> List[int]:
    """Return line indices where the iterable sort flag appears."""
    lines = src.splitlines()
    indices: List[int] = []
    for i, line in enumerate(lines):
        if flag_exists(FLAG_NAME, line):
            indices.append(i)
    return indices


def _collect_iterable_block(lines: List[str], flag_idx: int) -> Tuple[int, int]:
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


def reorder_flagged_iterables(src: str) -> str:
    """Sort items of flagged iterable blocks (typically list literals) alphabetically.

    - Looks for lines with '# filestate: python-iterable-sort'.
    - Sorts the contiguous following element lines until a blank line or closing bracket.
    - Stable for comment/blank lines (not included in sort) and preserves indentation/commas.
    - If already sorted, returns original src unchanged.
    """
    lines = src.splitlines()
    if not lines:
        return src

    flag_lines = _find_flag_line_indices(src)
    if not flag_lines:
        return src

    changed = False

    for flag_idx in reversed(flag_lines):
        start, end = _collect_iterable_block(lines, flag_idx)
        if start >= end:
            continue
        block = lines[start:end]
        # Consider only non-comment lines in the block; the spec implies items
        # are expressed as one item per line.
        # We'll sort the entire block lines by their stripped text.
        sorted_block = sorted(block, key=lambda s: s.strip().lower())
        if sorted_block != block:
            lines[start:end] = sorted_block
            changed = True

    return "\n".join(lines) if changed else src
