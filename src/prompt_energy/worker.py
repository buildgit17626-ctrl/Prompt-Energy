"""Trusted worker bootstrap, launched by absolute path with Python -P -s -S -B."""

import ast
import builtins
import importlib
import json
import operator
import random
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

# Expose selected computation APIs rather than complete module namespaces (which
# can themselves contain os/sys references). Never add file/process APIs here.
EXPORTS = {
    "hashlib": "md5 sha1 sha224 sha256 sha384 sha512 blake2b blake2s",
    "math": "ceil floor trunc fabs factorial gcd lcm isqrt sqrt exp log log2 log10 pow "
    "sin cos tan asin acos atan atan2 degrees radians hypot isclose isfinite "
    "isinf isnan fsum prod comb perm copysign modf frexp ldexp pi e tau inf nan",
    "itertools": "accumulate chain combinations combinations_with_replacement compress "
    "count cycle dropwhile filterfalse groupby islice pairwise permutations "
    "product repeat starmap takewhile tee zip_longest",
    "functools": "reduce lru_cache cache partial cmp_to_key",
    "collections": "Counter defaultdict deque OrderedDict",
    "heapq": "heapify heappush heappop heappushpop heapreplace nlargest nsmallest merge",
    "bisect": "bisect bisect_left bisect_right insort insort_left insort_right",
    "re": "compile match fullmatch search findall finditer split sub subn escape "
    "IGNORECASE MULTILINE DOTALL ASCII",
    "string": "ascii_letters ascii_lowercase ascii_uppercase digits hexdigits "
    "octdigits punctuation whitespace printable",
    "typing": "List Dict Tuple Set FrozenSet Optional Union Any Iterable Sequence Callable",
    "random": "random randint randrange choice choices sample shuffle uniform seed Random",
    "copy": "copy deepcopy",
    "fractions": "Fraction",
    "decimal": "Decimal",
    "statistics": "mean median mode multimode stdev pstdev variance pvariance",
    "operator": "add sub mul truediv floordiv mod pow neg abs eq ne lt le gt ge "
    "and_ or_ xor not_ itemgetter",
}


def arithmetic_only(expression: str) -> int | float:
    """Support HumanEval/160 without exposing Python's eval or compiled execution.

    The exact same replacement applies to references and future model solutions.
    Only numeric constants and arithmetic operators are interpreted.
    """
    if not isinstance(expression, str) or len(expression) > 10_000:
        raise ValueError("arithmetic_expression_limit")
    tree = ast.parse(expression, mode="eval")
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            return operators[type(node.op)](visit(node.left), visit(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd | ast.USub):
            return visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        raise ValueError("only_numeric_arithmetic_allowed")

    return visit(tree.body)


def deny_network(event: str, args: tuple) -> None:
    """Deny audited socket/DNS operations before any candidate code runs.

    This is a second Python-level layer, not an OS firewall or VM boundary.
    """
    if event.startswith("socket."):
        raise PermissionError("network_access_denied")


def main() -> int:
    """Execute only after the parent installs OS limits and sends the gate byte."""
    if sys.stdin.buffer.read(1) != b"G":
        return 2
    payload = json.loads(Path("input.json").read_text(encoding="utf-8"))
    sys.addaudithook(deny_network)
    random.seed(payload["seed"])
    modules = {
        name: SimpleNamespace(
            **{key: getattr(importlib.import_module(name), key) for key in exports.split()}
        )
        for name, exports in EXPORTS.items()
    }

    def limited_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level or name not in modules:
            raise ImportError("Import disallowed")
        return modules[name]

    names = (
        "abs all any ascii bin bool bytearray bytes callable chr complex dict divmod "
        "enumerate filter float format frozenset hash hex int isinstance issubclass iter "
        "len list map max min next oct ord pow print range repr reversed round set slice "
        "sorted str sum tuple zip Exception ValueError TypeError IndexError KeyError "
        "ZeroDivisionError AssertionError StopIteration RuntimeError NotImplementedError"
    )
    safe_builtins = {name: getattr(builtins, name) for name in names.split()}
    safe_builtins["__import__"] = limited_import
    safe_builtins["eval"] = arithmetic_only
    candidate_scope = {"__builtins__": safe_builtins, "__name__": "candidate"}
    outcome = {"status": "runtime_error", "reason": "unknown"}
    try:
        # Standard script loading occurs only in this resource-limited worker.
        # The harness never calls eval/exec on candidate text.
        candidate_scope = runpy.run_path("candidate.py", init_globals=candidate_scope)
        candidate = candidate_scope[payload["entry_point"]]
        # Trusted benchmark tests cannot be overwritten by candidate definitions.
        test_scope = runpy.run_path("checks.py")
        test_scope["check"](candidate)
        outcome = {"status": "passed", "reason": ""}
    except MemoryError:
        outcome = {"status": "memory_limit", "reason": "allocation_refused"}
    except AssertionError:
        outcome = {"status": "failed", "reason": "assertion_failed"}
    except BaseException as exc:
        # Do not invoke arbitrary candidate-defined repr/str while reporting errors.
        outcome = {"status": "runtime_error", "reason": type(exc).__name__}
    Path("outcome.json").write_text(json.dumps(outcome), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
