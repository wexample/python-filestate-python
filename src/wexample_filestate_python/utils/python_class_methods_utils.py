from __future__ import annotations

import libcst as cst

# Dunder ordering groups per guideline
DUnderGroups: list[list[str]] = [
    ["__new__", "__init__"],
    ["__repr__", "__str__"],
    ["__lt__", "__le__", "__eq__", "__ne__", "__gt__", "__ge__", "__hash__"],
    ["__bool__"],
    ["__getattribute__", "__getattr__", "__setattr__", "__delattr__"],
    ["__len__", "__iter__", "__getitem__", "__setitem__", "__delitem__"],
    ["__call__"],
    ["__enter__", "__exit__", "__aenter__", "__aexit__"],
    ["__await__", "__aiter__", "__anext__"],
    ["__get__", "__set__", "__delete__", "__getstate__", "__setstate__"],
]

# Build a lookup map: name -> (group_index, index_within_group)
_DUNDER_ORDER: dict[str, tuple[int, int]] = {}
for gi, group in enumerate(DUnderGroups):
    for si, name in enumerate(group):
        _DUNDER_ORDER[name] = (gi, si)


def ensure_order_class_methods_in_module(module: cst.Module) -> cst.Module:
    changed = False
    new_body = list(module.body)
    for idx, node in enumerate(new_body):
        if isinstance(node, cst.ClassDef):
            updated = reorder_class_methods(node)
            if updated is not node:
                new_body[idx] = updated
                changed = True
    if not changed:
        return module
    return module.with_changes(body=new_body)


def reorder_class_methods(classdef: cst.ClassDef) -> cst.ClassDef:
    """Reorder methods and properties in the class body according to rules 13-17.

    - Dunder methods ordered in logical groups
    - Classmethods sorted public A–Z then private A–Z
    - Staticmethods sorted public A–Z then private A–Z
    - Properties grouped by base name (getter, setter, deleter together), groups A–Z
    - Instance methods sorted public A–Z then private/protected A–Z

    Non-method nodes (attributes, inner classes, etc.) retain their relative positions; the
    collection of methods/properties is reordered as a single subsequence in place of the
    original methods/properties (stable placement among non-method nodes).
    """
    body_list = list(classdef.body.body)

    # Collect method nodes and their indices
    method_indices: list[int] = []
    method_nodes: list[cst.FunctionDef] = []
    for idx, node in enumerate(body_list):
        if _is_method_node(node):
            method_indices.append(idx)
            method_nodes.append(node)

    if not method_nodes:
        return classdef

    # Classify
    dunders: list[dict] = []
    classmethods: list[dict] = []
    staticmethods: list[dict] = []
    properties: list[dict] = []
    instances: list[dict] = []

    for f in method_nodes:
        kind, meta = _classify_method(f)
        if kind == "dunder":
            dunders.append(meta)
        elif kind == "classmethod":
            classmethods.append(meta)
        elif kind == "staticmethod":
            staticmethods.append(meta)
        elif kind == "property":
            properties.append(meta)
        else:
            instances.append(meta)

    # Order dunders by (group, within) then keep unknown dunders after known, alpha by name
    known = [m for m in dunders if m["order"][0] != 999]
    unknown = [m for m in dunders if m["order"][0] == 999]
    known_sorted = sorted(known, key=lambda m: (m["order"][0], m["order"][1]))
    unknown_sorted = sorted(unknown, key=lambda m: _sort_key_alpha(m["name"]))
    dunder_ordered = [m["node"] for m in known_sorted + unknown_sorted]

    # Sort classmethods/staticmethods and instances: public first then private
    def sort_by_visibility(items: list[dict]) -> list[cst.FunctionDef]:
        pub = [i for i in items if not _is_private(i["name"])]
        priv = [i for i in items if _is_private(i["name"])]
        pub_sorted = [
            i["node"] for i in sorted(pub, key=lambda x: _sort_key_alpha(x["name"]))
        ]
        priv_sorted = [
            i["node"] for i in sorted(priv, key=lambda x: _sort_key_alpha(x["name"]))
        ]
        return pub_sorted + priv_sorted

    classmethods_ordered = sort_by_visibility(classmethods)
    staticmethods_ordered = sort_by_visibility(staticmethods)
    instances_ordered = sort_by_visibility(instances)

    # Group properties by base name, order getter, setter, deleter within group
    prop_groups: dict[str, dict[str, cst.FunctionDef | None]] = {}
    for m in properties:
        base = m["base"]
        kind = m["kind"]
        node = m["node"]
        g = prop_groups.setdefault(
            base, {"getter": None, "setter": None, "deleter": None}
        )
        g[kind] = node

    def prop_group_to_nodes(base: str, g: dict[str, cst.FunctionDef | None]):
        order = []
        if g.get("getter") is not None:
            order.append(g["getter"])  # type: ignore
        if g.get("setter") is not None:
            order.append(g["setter"])  # type: ignore
        if g.get("deleter") is not None:
            order.append(g["deleter"])  # type: ignore
        return order

    props_ordered: list[cst.FunctionDef] = []
    for base in sorted(prop_groups.keys(), key=lambda n: n.lower()):
        props_ordered.extend(prop_group_to_nodes(base, prop_groups[base]))

    # Final ordered list: dunder -> classmethods -> staticmethods -> properties -> instances
    ordered_methods: list[cst.FunctionDef] = (
        dunder_ordered
        + classmethods_ordered
        + staticmethods_ordered
        + props_ordered
        + instances_ordered
    )

    # If order unchanged, return original
    if ordered_methods == method_nodes:
        return classdef

    # Reconstruct body: replace the method nodes subsequence positions with ordered ones,
    # keeping non-method nodes in place.
    new_body = list(body_list)
    for pos, new_node in zip(method_indices, ordered_methods):
        new_body[pos] = new_node

    new_suite = classdef.body.with_changes(body=new_body)
    return classdef.with_changes(body=new_suite)


def _classify_method(func: cst.FunctionDef) -> tuple[str, dict]:
    """Classify a FunctionDef into one of: dunder, classmethod, staticmethod, property, instance.
    Returns (kind, meta) where meta provides extra info like name, dunder order, property base/kind.
    """
    name = func.name.value
    # Properties first (they may also have classmethod/staticmethod in theory, ignore that)
    base, pkind = _property_kind(func)
    if base is not None:
        return "property", {"base": base, "kind": pkind, "node": func}
    # Classmethod / staticmethod
    if _has_decorator(func, "classmethod"):
        return "classmethod", {"name": name, "node": func}
    if _has_decorator(func, "staticmethod"):
        return "staticmethod", {"name": name, "node": func}
    # Dunder methods
    if _is_dunder(name):
        order = _DUNDER_ORDER.get(name, (999, 999))
        return "dunder", {"name": name, "order": order, "node": func}
    # Instance method
    return "instance", {"name": name, "node": func}


def _has_decorator(func: cst.FunctionDef, decorator_name: str) -> bool:
    for dec in func.decorators:
        expr = dec.decorator
        # @decorator
        if isinstance(expr, cst.Name) and expr.value == decorator_name:
            return True
        # @module.decorator
        if (
            isinstance(expr, cst.Attribute)
            and isinstance(expr.attr, cst.Name)
            and expr.attr.value == decorator_name
        ):
            return True
    return False


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _is_method_node(node: cst.CSTNode) -> bool:
    return isinstance(node, cst.FunctionDef)


def _is_private(name: str) -> bool:
    return name.startswith("_") and not _is_dunder(name)


def _property_kind(func: cst.FunctionDef) -> tuple[str | None, str | None]:
    """Return (base_name, kind) where kind in {getter, setter, deleter} or (None, None).
    For setters/deleters, decorator is like @<name>.setter or @<name>.deleter.
    """
    # Getter: @property on a function whose name is the property name
    if _has_decorator(func, "property"):
        return func.name.value, "getter"
    # Setter/deleter: look for Attribute decorator <name>.setter / <name>.deleter
    for dec in func.decorators:
        expr = dec.decorator
        if isinstance(expr, cst.Attribute) and isinstance(expr.attr, cst.Name):
            if expr.attr.value in {"setter", "deleter"}:
                # base name is left side of the attribute if it's a Name
                base = expr.value
                if isinstance(base, cst.Name):
                    return base.value, (
                        "setter" if expr.attr.value == "setter" else "deleter"
                    )
    return None, None


def _sort_key_alpha(name: str) -> tuple:
    # Case-insensitive, underscore after letters
    return (name.lstrip("_").lower(), name.startswith("_"))
