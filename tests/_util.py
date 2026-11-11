from __future__ import annotations

import ast
import os
import sys
from typing import Literal

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "py_modules"))

# Local Handheld Daemon checkout used as the reference implementation.
HHD_SRC = os.environ.get(
    "HHD_SRC", os.path.join(ROOT, "..", "hhd", "src", "hhd")
)


def load_hhd_functions(relpath: str, names: list[str]) -> dict | None:
    """Load selected top-level functions from an HHD source file.

    Only the named function definitions are executed (not HHD's imports), so
    HHD's runtime dependencies don't need to be installed. Returns None if
    the HHD checkout isn't available.
    """
    path = os.path.join(HHD_SRC, relpath)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        tree = ast.parse(f.read())

    wanted = set(names)
    body = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            body.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in wanted for t in node.targets
        ):
            body.append(node)
    module = ast.Module(body=body, type_ignores=[])
    ns: dict = {"Literal": Literal}
    exec(compile(module, path, "exec"), ns)
    missing = wanted - ns.keys()
    if missing:
        raise AssertionError(f"HHD functions not found in {relpath}: {missing}")
    return ns
