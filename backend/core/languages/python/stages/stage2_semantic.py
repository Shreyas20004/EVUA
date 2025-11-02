from pathlib import Path
import ast
import json
from typing import List, Dict, Any
from utils.file_ops import write_json_atomic  # atomic write helper

# -----------------------------
# Data Model
# -----------------------------
class SemanticResult:
    """
    Stores info about a detected semantic risk.
    """
    def __init__(self, filename: str, lineno: int, message: str, fixed_code: str = None):
        self.filename = filename
        self.lineno = lineno
        self.message = message
        self.fixed_code = fixed_code

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "lineno": self.lineno,
            "message": self.message,
            "fixed_code": self.fixed_code,
        }


# -----------------------------
# AST-based semantic detectors
# -----------------------------

def detect_division_uses(tree: ast.Module) -> List[ast.BinOp]:
    """
    Detect all '/' divisions in Python 2 code which may produce integer division.
    """
    return [node for node in ast.walk(tree) if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)]


def wrap_map_if_list_usage(tree: ast.Module) -> List[Dict[str, Any]]:
    """
    Detect patterns like map(f, seq)[0] or len(map(...)) and flag them or fix by wrapping with list().
    Returns a list of {'node', 'lineno', 'fixed_code'} dicts.
    """
    fixes = []

    class MapVisitor(ast.NodeVisitor):
        def visit_Subscript(self, node):
            if isinstance(node.value, ast.Call) and getattr(node.value.func, 'id', None) == "map":
                # Example: a = map(f, seq)[0]
                fixes.append({
                    "node": node,
                    "lineno": node.lineno,
                    "fixed_code": f"list({ast.unparse(node.value)})[{ast.unparse(node.slice)}]"
                })
            self.generic_visit(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id in {"len", "sum"}:
                for arg in node.args:
                    if isinstance(arg, ast.Call) and getattr(arg.func, 'id', None) == "map":
                        fixes.append({
                            "node": node,
                            "lineno": node.lineno,
                            "fixed_code": f"{ast.unparse(node.func)}(list({ast.unparse(arg)}))"
                        })
            self.generic_visit(node)

    MapVisitor().visit(tree)
    return fixes


def detect_keys_items_usage(tree: ast.Module) -> List[Dict[str, Any]]:
    """
    Detect dict.keys(), dict.items(), dict.values() usage in Python 2, which returns lists in Py2 but views in Py3.
    """
    warnings = []

    class DictVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Attribute) and node.func.attr in {"keys", "items", "values"}:
                warnings.append({
                    "lineno": node.lineno,
                    "call": ast.unparse(node)
                })
            self.generic_visit(node)

    DictVisitor().visit(tree)
    return warnings


# -----------------------------
# Public function
# -----------------------------

def semantic_fix(in_dir: Path, out_dir: Path) -> List[SemanticResult]:
    """
    Analyze all .py files in `in_dir` for semantic-risk patterns and apply safe fixes if possible.
    Writes fixed files to `out_dir` and outputs semantic_metadata.json.
    """
    results: List[SemanticResult] = []
    out_dir.mkdir(exist_ok=True, parents=True)

    for py_file in in_dir.glob("*.py"):
        code = py_file.read_text(encoding="utf-8")
        tree = ast.parse(code)

        # 1) Division detection
        for node in detect_division_uses(tree):
            results.append(SemanticResult(
                filename=str(py_file),
                lineno=node.lineno,
                message="Potential integer division; consider 'from __future__ import division'",
                fixed_code=None
            ))

        # 2) Map usage wrapping
        for fix in wrap_map_if_list_usage(tree):
            results.append(SemanticResult(
                filename=str(py_file),
                lineno=fix["lineno"],
                message="map() used in index/len context; wrapped with list()",
                fixed_code=fix["fixed_code"]
            ))

        # 3) Dict keys/items/values usage
        for warn in detect_keys_items_usage(tree):
            results.append(SemanticResult(
                filename=str(py_file),
                lineno=warn["lineno"],
                message=f"dict.{warn['call'].split('.')[-1]}() usage may behave differently in Python 3",
                fixed_code=None
            ))

        # Apply fixes to code
        fixed_code_lines = code.splitlines()
        for r in [res for res in results if res.filename == str(py_file) and res.fixed_code]:
            fixed_code_lines[r.lineno - 1] = r.fixed_code
        fixed_code = "\n".join(fixed_code_lines)
        (out_dir / py_file.name).write_text(fixed_code, encoding="utf-8")

    # Save metadata
    meta_path = out_dir / "semantic_metadata.json"
    write_json_atomic(meta_path, [r.to_dict() for r in results])

    return results
