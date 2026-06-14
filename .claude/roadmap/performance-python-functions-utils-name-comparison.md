# Performance: avoid double-list allocation in module_functions_already_ordered

**File:** `src/wexample_filestate_python/utils/python_functions_utils.py`

**What:** `module_functions_already_ordered` ends with:

```python
return [g.name for g in groups] == [g.name for g in expected]
```

This materialises two full name-lists just to compare them element-wise.
Because `sort_function_groups` is a pure permutation of the input, both lists
are guaranteed to have the same length, so we can use a short-circuit generator
comparison instead:

```python
return all(a.name == b.name for a, b in zip(groups, expected))
```

**Expected gain:** Avoids two heap allocations (`list` + `str` refs for each
group name) and exits as soon as the first mismatch is found instead of always
building both full lists before comparing. The gain scales with module size but
matters most on files that are *almost* ordered (only the last group differs),
where the generator exits after the first comparison while the list approach
always finishes both list comprehensions.

**Blocker:** None — `sort_function_groups` always returns a permutation of its
input, so `len(groups) == len(expected)` is invariant and the `zip`-based
comparison is semantically equivalent.
