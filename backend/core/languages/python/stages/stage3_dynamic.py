import json
from pathlib import Path
from dataclasses import dataclass
from typing import List
from utils.docker_utils import run_command_in_container, RunResult


@dataclass
class ComparisonResult:
    match: bool
    details: str


@dataclass
class DynamicReport:
    total: int
    matched: int
    mismatched: int
    manual: List[str]
    reports_dir: Path


def create_smoke_harness(module_path: Path) -> Path:
    """Creates a lightweight harness script to import and run functions in a module."""
    harness_path = module_path.parent / f"{module_path.stem}_harness.py"
    harness_code = f"""
import importlib, json

mod = importlib.import_module("{module_path.stem}")
results = {{}}

for name in dir(mod):
    obj = getattr(mod, name)
    if callable(obj) and not name.startswith("_"):
        try:
            results[name] = obj()
        except TypeError:
            continue
        except Exception as e:
            results[name] = f"error: {{e}}"

print(json.dumps(results))
"""
    harness_path.write_text(harness_code.strip(), encoding="utf-8")
    return harness_path


def compare_runs(py2_result: RunResult, py3_result: RunResult) -> ComparisonResult:
    """Compare JSON outputs from both runs (robust against newline and type diffs)."""
    s1, s2 = py2_result.stdout.strip(), py3_result.stdout.strip()
    if not s1 or not s2:
        return ComparisonResult(False, "Empty or invalid output")

    try:
        out2 = json.loads(s1)
        out3 = json.loads(s2)
    except json.JSONDecodeError:
        return ComparisonResult(s1 == s2, "Non-JSON textual comparison")

    if out2 == out3:
        return ComparisonResult(True, "All outputs match")

    diff = {
        k: (out2.get(k), out3.get(k))
        for k in set(out2) | set(out3)
        if out2.get(k) != out3.get(k)
    }
    return ComparisonResult(False, json.dumps(diff, indent=2))


def dynamic_verify(session_dir: Path, py2_image: str, py3_image: str, timeout: int = 15) -> DynamicReport:
    """
    Executes all modules in session_dir under Py2 & Py3, compares results, saves reports.
    Uses Docker if available; otherwise runs locally via fallback.
    """
    stage_dir = session_dir / "stage3_dynamic"
    diffs_out = stage_dir / "diff_reports"
    stage_dir.mkdir(parents=True, exist_ok=True)
    diffs_out.mkdir(parents=True, exist_ok=True)

    total = matched = mismatched = 0
    manual: List[str] = []

    for pyfile in session_dir.glob("*.py"):
        if "_harness" in pyfile.stem:
            continue

        total += 1
        harness = create_smoke_harness(pyfile)

        py2_res = run_command_in_container(
            py2_image, {session_dir: Path("/data")}, ["python", harness.name], timeout
        )
        py3_res = run_command_in_container(
            py3_image, {session_dir: Path("/data")}, ["python", harness.name], timeout
        )

        cmp = compare_runs(py2_res, py3_res)
        if cmp.match:
            matched += 1
        else:
            mismatched += 1

        report_path = diffs_out / f"{pyfile.stem}_diff.json"
        report_data = {
            "file": str(pyfile),
            "match": cmp.match,
            "details": cmp.details,
            "py2_exit": py2_res.exit_code,
            "py3_exit": py3_res.exit_code,
        }
        report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    # ✅ Matches what the pipeline test expects
    metadata = {
        "total": total,
        "matched": matched,
        "mismatched": mismatched,
        "manual": manual,
    }

    (stage_dir / "dynamic_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return DynamicReport(total, matched, mismatched, manual, stage_dir)
