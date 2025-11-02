import json
from pathlib import Path
from dataclasses import dataclass
from typing import List

from core.languages.python.stages.stage4_repair import attempt_repairs, ComparisonResult
from core.languages.python.stages.stage3_dynamic import dynamic_verify


@dataclass
class RepairSummary:
    total_files: int
    repaired: int
    still_failing: int
    attempts: int
    reports_dir: Path


def run_repair_loop(session_dir: Path, max_attempts: int = 3) -> RepairSummary:
    """
    Orchestrates automated repair loop:
    - Reads failed diff reports from dynamic stage
    - Calls language-specific repair
    - Re-runs dynamic verification until all match or attempts exhausted
    """
    diff_dir = session_dir / "stage3_dynamic" / "diff_reports"
    if not diff_dir.exists():
        raise FileNotFoundError(f"Diff reports not found at {diff_dir}")

    py2_image = "python:2.7"
    py3_image = "python:3.11"

    total = 0
    repaired = 0
    still_failing = 0

    for attempt_idx in range(1, max_attempts + 1):
        failing_files: List[Path] = []

        # --- Step 1: Collect mismatched reports ---
        for report_path in diff_dir.glob("*_diff.json"):
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
            if not report_data.get("match", True):
                failing_files.append(Path(report_data["file"]))

        if not failing_files:
            break  # all fixed

        total = len(failing_files)
        print(f"[RepairLoop] Attempt {attempt_idx}/{max_attempts} | Failing files: {len(failing_files)}")

        # --- Step 2: Attempt repairs ---
        for f in failing_files:
            cmp = ComparisonResult(
                file_path=str(f),
                py2_output="unknown",
                py3_output="unknown",
                match=False,
                diff="",
            )
            result = attempt_repairs(cmp, session_dir)
            if result.repaired:
                repaired += 1
            else:
                still_failing += 1

        # --- Step 3: Re-run dynamic verification ---
        print("[RepairLoop] Re-running dynamic verification...")
        dynamic_verify(session_dir, py2_image, py3_image, timeout=15)

    summary = RepairSummary(
        total_files=total,
        repaired=repaired,
        still_failing=still_failing,
        attempts=attempt_idx,
        reports_dir=session_dir / "stage4_repair",
    )

    # --- Save metadata (Path → str for JSON) ---
    stage_dir = summary.reports_dir
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / "repair_summary.json").write_text(
        json.dumps(
            {k: str(v) if isinstance(v, Path) else v for k, v in summary.__dict__.items()},
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"[RepairLoop] Completed {attempt_idx} attempts. Repaired: {repaired}/{total}")
    return summary
