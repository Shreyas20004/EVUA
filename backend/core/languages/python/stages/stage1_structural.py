# core/languages/python/stages/stage1_structural.py

from pathlib import Path
from typing import List, Dict
import json
from lib2to3.refactor import RefactoringTool, get_fixers_from_package

FileResult = Dict[str, any]  # Simple dict for MVP

# Custom simple fixer for print >> and long edge cases
def apply_custom_fixers(file_path: Path) -> Dict:
    """
    Applies minimal deterministic custom fixes to a Python 2 file.
    Currently handles:
      - print >> sys.stderr → print(..., file=sys.stderr)
      - long literals like 123L → 123
    """
    changes = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for lineno, line in enumerate(lines, 1):
        original = line

        # fix print >>
        if "print >>" in line:
            line = line.replace("print >>", "print(")
            if not line.rstrip().endswith(")"):
                line = line.rstrip() + ")\n"
            changes.append(f"print >> converted at line {lineno}")

        # fix long literals like 123L
        if "L" in line:
            import re
            new_line = re.sub(r"(\d+)L", r"\1", line)
            if new_line != line:
                line = new_line
                changes.append(f"long literal fixed at line {lineno}")

        new_lines.append(line)

    # overwrite file
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return {"file": str(file_path), "changes": changes}


def structural_convert(in_dir: Path, out_dir: Path) -> List[FileResult]:
    """
    Run lib2to3 conversion + custom fixers.
    Writes results to stage1_2to3/ and stage1_custom/, plus stage1_metadata.json.
    """
    out_dir_2to3 = out_dir / "stage1_2to3"
    out_dir_custom = out_dir / "stage1_custom"
    out_dir_2to3.mkdir(parents=True, exist_ok=True)
    out_dir_custom.mkdir(parents=True, exist_ok=True)

    # Prepare lib2to3
    fixers = get_fixers_from_package("lib2to3.fixes")
    refactor_tool = RefactoringTool(fixers)

    results = []

    for py_file in in_dir.rglob("*.py"):
        relative_path = py_file.relative_to(in_dir)

        # --- lib2to3 conversion ---
        with open(py_file, "r", encoding="utf-8") as f:
            code = f.read()
        try:
            new_code = str(refactor_tool.refactor_string(code, str(py_file)))
        except Exception as e:
            new_code = code  # fallback
            print(f"[lib2to3] Error processing {py_file}: {e}")

        # write lib2to3 output
        out_file_2to3 = out_dir_2to3 / relative_path
        out_file_2to3.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file_2to3, "w", encoding="utf-8") as f:
            f.write(new_code)

        # --- custom fixes ---
        out_file_custom = out_dir_custom / relative_path
        out_file_custom.parent.mkdir(parents=True, exist_ok=True)
        # copy lib2to3 code first
        with open(out_file_custom, "w", encoding="utf-8") as f:
            f.write(new_code)

        custom_res = apply_custom_fixers(out_file_custom)

        results.append({
            "file": str(relative_path),
            "lib2to3": str(out_file_2to3),
            "custom": custom_res,
        })

    # Write stage1 metadata
    metadata_path = out_dir / "stage1_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    return results


# --- Simple test ---
if __name__ == "__main__":
    src = Path("./sessions/test_session/stage0_preprocessed")
    out = Path("./sessions/test_session")
    res = structural_convert(src, out)
    print(f"Processed {len(res)} files. Metadata at {out / 'stage1_metadata.json'}")
