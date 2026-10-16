"""Conservative syntax policy; defense in depth, not a Python security boundary."""

import ast

ALLOWED_IMPORTS = frozenset(
    {
        "math",
        "itertools",
        "functools",
        "collections",
        "heapq",
        "bisect",
        "re",
        "string",
        "typing",
        "random",
        "copy",
        "fractions",
        "decimal",
        "statistics",
        "operator",
        "hashlib",
    }
)
BLOCKED_NAMES = frozenset(
    {
        "open",
        "exec",
        "compile",
        "input",
        "breakpoint",
        "help",
        "exit",
        "quit",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
        "dir",
        "type",
        "object",
        "super",
        "memoryview",
        "classmethod",
        "staticmethod",
        "property",
    }
)


def check_source(source: str, max_bytes: int = 100_000) -> None:
    """Raise ValueError for code outside the supported computation-only subset."""
    if len(source.encode("utf-8")) > max_bytes:
        raise ValueError("source_size_limit")
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("invalid_syntax") from exc
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef | ast.Global | ast.Nonlocal | ast.AsyncFunctionDef):
            raise ValueError(f"blocked_syntax:{type(node).__name__}")
        if isinstance(node, ast.Name) and (node.id.startswith("__") or node.id in BLOCKED_NAMES):
            raise ValueError(f"blocked_name:{node.id}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ValueError(f"blocked_attribute:{node.attr}")
        if isinstance(node, ast.Import):
            if any(alias.name not in ALLOWED_IMPORTS for alias in node.names):
                raise ValueError("blocked_import")
        if isinstance(node, ast.ImportFrom):
            if node.level or node.module not in ALLOWED_IMPORTS:
                raise ValueError("blocked_import")
            if any(alias.name == "*" or alias.name.startswith("_") for alias in node.names):
                raise ValueError("blocked_import_member")
        if isinstance(node, ast.FunctionDef | ast.arg | ast.alias):
            names = (
                [node.name]
                if isinstance(node, ast.FunctionDef)
                else [node.arg]
                if isinstance(node, ast.arg)
                else [node.asname or node.name]
            )
            if any(name.startswith("__") or name in BLOCKED_NAMES for name in names):
                raise ValueError("blocked_binding")
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            raise ValueError("blocked_decorator")
