import json
from pathlib import Path
from dataclasses import dataclass, asdict
import difflib

# ---------- Data Models ----------

@dataclass
class ComparisonResult:
    file_path: str
    py2_output: str
    py3_output: str
    match: bool
    diff: str

@dataclass
class RepairAttempt:
    strategy: str
    success: bool
    diff_after: str

@dataclass
class RepairAttempts:
    file_path: str
    applied: list
    repaired: bool


# ---------- Core Repair Logic ----------

def attempt_repairs(file_report: ComparisonResult, session_dir: Path) -> RepairAttempts:
    """
    Try a sequence of simple automated repair strategies on a mismatched module.
    Re-run verification after each repair to check if outputs align.
    """
    file_path = Path(file_report.file_path)
    src = file_path.read_text(encoding="utf-8")

    strategies = [
        ("wrap_iterables", _wrap_iterables),
        ("safe_division", _fix_division),
        ("explicit_str_cast", _explicit_str_cast),
        ("encode_decode_fix", _encode_decode_fix),
    ]

    applied = []
    repaired = False
    max_attempts = 3

    for name, func in strategies[:max_attempts]:
        new_src = func(src)
        if new_src == src:
            continue  # no change

        file_path.write_text(new_src, encoding="utf-8")

        # For MVP, simulate verification by re-comparing output strings
        diff_after = _diff_text(file_report.py2_output, file_report.py3_output)
        success = diff_after.strip() == ""
        applied.append(RepairAttempt(name, success, diff_after))

        if success:
            repaired = True
            break
        else:
            src = new_src  # continue chaining if needed

    # Save metadata
    metadata_path = session_dir / "repair_metadata.json"
    metadata = RepairAttempts(
        file_path=str(file_path),
        applied=[asdict(a) for a in applied],
        repaired=repaired,
    )
    metadata_path.write_text(json.dumps(asdict(metadata), indent=2), encoding="utf-8")

    # Also write updated diff report
    diff_report_path = session_dir / "diff_reports"
    diff_report_path.mkdir(exist_ok=True)
    (diff_report_path / f"{file_path.stem}_diff_after.json").write_text(
        json.dumps({"diff_after": applied[-1].diff_after if applied else file_report.diff}, indent=2),
        encoding="utf-8"
    )

    return metadata


# ---------- Simple Repair Strategies ----------

def _wrap_iterables(src: str) -> str:
    # Replace map/filter/object iteration with list()
    if "map(" in src and "list(" not in src:
        return src.replace("map(", "list(map(") + ")"
    return src

def _fix_division(src: str) -> str:
    # Convert integer division 'a/b' to float division explicitly
    return src.replace("/", "/ 1.0*") if "/" in src and "//" not in src else src

def _explicit_str_cast(src: str) -> str:
    # Add explicit str() cast around print arguments if missing
    if "print(" in src and "str(" not in src:
        return src.replace("print(", "print(str(") + ")"
    return src

def _encode_decode_fix(src: str) -> str:
    # Fix .decode()/.encode() missing calls
    if ".decode(" not in src and ".encode(" not in src and "'utf" in src:
        return src.replace("'utf", ".encode('utf")
    return src


# ---------- Helpers ----------

def _diff_text(a: str, b: str) -> str:
    return "\n".join(difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm=""))
