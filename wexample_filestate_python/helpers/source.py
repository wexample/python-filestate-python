def source_infer_simple_return_type(
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
) -> str | None:
    # Collect all return value nodes
    returns: List[ast.Return] = [n for n in ast.walk(node) if isinstance(n, ast.Return)]

    # If no return statements at all -> None
    if not returns:
        return "None"

    kinds: set[str] = set()
    for ret in returns:
        val = ret.value
        if val is None:
            kinds.add("None")
        elif isinstance(val, ast.Constant):
            if isinstance(val.value, bool):
                kinds.add("bool")
            elif isinstance(val.value, str):
                kinds.add("str")
            elif isinstance(val.value, int):
                kinds.add("int")
            elif isinstance(val.value, float):
                kinds.add("float")
            elif val.value is None:
                kinds.add("None")
            else:
                return None
        else:
            # Non-literal return -> give up (phase 1)
            return None

    if len(kinds) == 1:
        return next(iter(kinds))
    # Mixed types -> give up in phase 1
    return None


def source_annotate_simple_returns(src: str) -> str:
    """Add a return annotation to def lines where source_infer_simple_return_type returns a type.

    We use a conservative regex rewrite limited to the function signature line to avoid
    reformatting the whole file. Works for simple cases; multi-line defs are handled by
    adding the annotation before the colon in the first line.
    """
    tree = ast.parse(src)

    # Collect function names that need annotation with their inferred type
    targets: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.returns is None
        ):
            t = source_infer_simple_return_type(node)
            if t is not None:
                targets.append((node.name, t))

    if not targets:
        return src

    # Apply replacements function by function.
    import re

    new_src = src
    for func_name, rtype in targets:
        # def <name>(...) [-> ...]?:  add -> rtype before colon if missing
        pattern = rf"(def\s+{re.escape(func_name)}\s*\([^\)]*\))\s*(->\s*[^:]+)?\s*:"
        repl = rf"\1 -> {rtype}:"
        new_src, n = re.subn(pattern, repl, new_src, count=1, flags=re.MULTILINE)
        # If we didn't match (e.g., decorators with async or multiline with newline in params), try async variant
        if n == 0:
            pattern_async = rf"(async\s+def\s+{re.escape(func_name)}\s*\([^\)]*\))\s*(->\s*[^:]+)?\s*:"
            new_src = re.sub(pattern_async, repl, new_src, count=1, flags=re.MULTILINE)

    return new_src
