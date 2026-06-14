# New rule: `# type: ignore` must include a specific error code

**Source**: *(new option — `option/python/type_ignore_require_code_option.py`)*
**Agent**: agent:rectifier-rules
**Bucket**: new-rule
**Severity**: feature

## Symptom
`# type: ignore` (no code) silences **every** type error on the line — including future ones that have nothing to do with the original suppression. Mypy's `--strict` flag (`enable_error_code=ignore-without-code`) catches it but is rarely on in this repo. Same applies to `# noqa` without ruff/flake8 codes.

## Suggested direction
Token-level scan (regex on the source text — no need for CST):
- Match `# type: ignore$` (and `# type: ignore ` with trailing comment) — flag as missing code.
- Match `# noqa$` / `# noqa ` — flag as missing code.

Two modes:
- **warn-only**: emit `target.io.warning(f"{path}:{lineno}: type: ignore without error code")`. Default.
- **auto-stamp**: rewrite to `# type: ignore[unknown]` so the file still works but a follow-up sweep highlights the placeholder for triage. Opt-in via flag.

Idempotent: re-running finds nothing once codes are in place. Cheap: line-by-line, no parse.
