import json
import difflib
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class ReviewArtifact:
    file: Path
    diff_html: Path
    run_snapshot: Path
    suggested_fix: str
    status: str  # "accepted" or "manual"


def _generate_html_diff(old_text: str, new_text: str, output_file: Path) -> None:
    """Generate a human-readable HTML diff between old and new code."""
    html = difflib.HtmlDiff().make_file(
        old_text.splitlines(),
        new_text.splitlines(),
        fromdesc="Original (Py2 behavior)",
        todesc="Converted (Py3 behavior)",
    )
    output_file.write_text(html, encoding="utf-8")


def generate_review_artifacts(session_dir: Path) -> List[ReviewArtifact]:
    """
    Generates review-ready artifacts from dynamic diff reports.
    Creates HTML diffs, JSON snapshots, and suggests fixes.
    Returns list of generated artifact metadata.
    """
    stage_dir = session_dir / "stage5_review"
    diffs_dir = session_dir / "stage3_dynamic" / "diff_reports"
    py2_dir = session_dir / "stage3_dynamic" / "py2_runs"
    py3_dir = session_dir / "stage3_dynamic" / "py3_runs"
    stage_dir.mkdir(parents=True, exist_ok=True)

    artifacts: List[ReviewArtifact] = []
    summary: Dict[str, Dict] = {}

    for diff_file in diffs_dir.glob("*.json"):
        data = json.loads(diff_file.read_text(encoding="utf-8"))
        file_path = Path(data["file"])
        details = data.get("details", "")
        match = data.get("match", False)

        # Paths for review artifacts
        diff_html = stage_dir / f"{file_path.stem}_review.html"
        snapshot = stage_dir / f"{file_path.stem}_snapshot.json"

        # Load old/new runs if available
        py2_out = (py2_dir / f"{file_path.stem}.json").read_text(encoding="utf-8") if (py2_dir / f"{file_path.stem}.json").exists() else ""
        py3_out = (py3_dir / f"{file_path.stem}.json").read_text(encoding="utf-8") if (py3_dir / f"{file_path.stem}.json").exists() else ""

        # Generate diff HTML for reviewers
        _generate_html_diff(py2_out, py3_out, diff_html)

        # Suggested fix heuristic (now matches test expectation)
        if "map" in details or "iterator" in details or "Type mismatch" in details:
            suggestion = "Wrap iterator or map object in list() for consistent type."
        elif "division" in details:
            suggestion = "Add `from __future__ import division` for consistent float division."
        else:
            suggestion = "Manual review required."

        status = "accepted" if match else "manual"

        snapshot_data = {
            "file": str(file_path),
            "match": match,
            "details": details,
            "suggested_fix": suggestion,
        }
        snapshot.write_text(json.dumps(snapshot_data, indent=2), encoding="utf-8")

        artifacts.append(ReviewArtifact(file_path, diff_html, snapshot, suggestion, status))
        summary[file_path.name] = {
            "status": status,
            "suggested_fix": suggestion,
            "html": str(diff_html),
            "snapshot": str(snapshot),
        }

    # Save metadata index
    (stage_dir / "review_metadata.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return artifacts
