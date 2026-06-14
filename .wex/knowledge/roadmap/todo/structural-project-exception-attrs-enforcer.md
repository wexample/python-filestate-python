# Structural: enforce project exception convention (attrs base_class + `_build_message`)

**Source**: *(new option — `option/python/enforce_exception_convention_option.py`)*
**Agent**: agent:rectifier-design
**Bucket**: structural
**Severity**: feature

## Background
Project memory `project_exceptions_attrs` records the decided shape:
> hiérarchie d'exceptions en `@base_class` kw_only : suggestions, message dérivé via méthode `_build_message()` (PAS Factory(takes_self) qui casse avec le linter de tri de champs), lire via `render_message()`, to_dict/collect_data fusionne les fields. Pas de __init__/__attrs_post_init__.

A lot of existing exception classes still use the old `class FooError(Exception): def __init__(self, msg, data=None): ...` shape. They should migrate to the new convention.

## Suggested direction
Two passes:
1. **Detector** (warn-only, ship first): LibCST visitor that finds `ClassDef` inheriting (directly or transitively, conservatively limited to direct base name match) from `Exception` / `RuntimeError` / a project base exception, and that:
   - is NOT decorated with `@base_class`, OR
   - defines `__init__` / `__attrs_post_init__`, OR
   - lacks a `_build_message` method.
   For each, emit `target.io.warning(f"{path}:{class_name}: legacy exception shape — migrate to @base_class + _build_message")`.

2. **Auto-fixer** (later, opt-in): given the detector's findings, rewrite the class:
   - Add `@base_class` decorator (and `from wexample_helpers.decorator.base_class import base_class` if absent).
   - Convert `__init__` parameters to `public_field(...)` declarations sorted per attrs kw_only rules.
   - Wrap message-building logic into `_build_message`.
   - Drop `__init__` / `__attrs_post_init__`.

Phase 1 alone is high-value: it makes the migration backlog visible in every rectification pass instead of being hidden behind tribal memory.
