# Structural: flag-driven hoist of repeated literals to module-level constant

**Source**: *(new option — `option/python/extract_repeated_literal_option.py`)*
**Agent**: agent:rectifier-design
**Bucket**: structural
**Severity**: feature

## Background
We already have a "flag-driven" pattern that's worked well: `# filestate: python-iterable-sort` and `# filestate: python-constant-sort`. Same shape can drive a constant-extraction rectifier without any semantic risk: the human chooses what to hoist; the rule only does the mechanical edit.

## Suggested direction
**Trigger**: `# filestate: extract-constant=NAME` on the line **above** a literal expression (string, int, tuple of literals).

**Behavior**:
1. Detect the marker via comment scanning. Capture the literal beneath it. Validate it is a `cst.SimpleString` / `cst.Integer` / `cst.Tuple` of literals — bail otherwise.
2. Scan the rest of the module for syntactically-identical occurrences (CST equality, not just string match — to avoid false positives in unrelated contexts).
3. Hoist a `NAME: Final = <literal>` to the top of the module (after the metadata block — reuse `target_index_for_module_metadata` from existing utils).
4. Replace every occurrence (including the original) with `cst.Name(NAME)`.
5. Remove the marker comment.

**Idempotency**: re-running the rule on the now-rectified module finds no marker → no-op. Clean.

Pairs naturally with `OrderConstantsOption`, which would then alpha-sort the hoisted constants if also marked.
