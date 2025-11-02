import inspect
from pathlib import Path
from typing import List
import textwrap

def generate_hypothesis_tests(module_path: Path, export_funcs: List[str]) -> List[Path]:
    """
    Auto-generate Hypothesis-based test files for selected functions in a module.
    """
    module_name = module_path.stem
    test_dir = module_path.parent / "fuzz_tests"
    test_dir.mkdir(exist_ok=True)

    generated_files = []

    for func in export_funcs:
        test_file = test_dir / f"test_{func}_fuzz.py"
        code = f"""
import importlib.util, sys, pathlib
from hypothesis import given, strategies as st

module_path = pathlib.Path(r"{module_path}")
spec = importlib.util.spec_from_file_location("{module_name}", module_path)
mod = importlib.util.module_from_spec(spec)
sys.modules["{module_name}"] = mod
spec.loader.exec_module(mod)

@given(st.integers(), st.integers())
def test_{func}_fuzz(a, b):
    # Function should not raise exceptions for integer inputs
    try:
        mod.{func}(a, b)
    except Exception as e:
        assert False, f"Function raised exception: {{e}}"
"""
        test_file.write_text(textwrap.dedent(code).strip(), encoding="utf-8")
        generated_files.append(test_file)

    return generated_files
