# core/languages/python/stages/stage0_preprocess.py

from pathlib import Path
import re
import json
from typing import List, Dict, Tuple

FileResult = Dict[str, any]

REPLACEMENTS = {
    "xrange": "range",
    "long": "int",
    "unicode": "str"
}


def safe_replace_tokens(code: str) -> Tuple[str, List[str]]:
    """
    Replace Python 2 tokens safely using regex.
    Returns new code and list of applied replacements.
    """
    changes = []
    new_code = code
    
    # Replace Python 2 type names (word boundaries to avoid partial matches)
    for old, new in REPLACEMENTS.items():
        pattern = r'\b' + old + r'\b'
        matches = re.findall(pattern, new_code)
        if matches:
            new_code = re.sub(pattern, new, new_code)
            changes.append(f"{old} → {new} ({len(matches)} occurrence(s))")
    
    # Fix print statements (Python 2 → Python 3)
    # Pattern: print followed by space and not already a function call
    print_pattern = r'^(\s*)print\s+(?!\()(.+)$'
    
    lines = new_code.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Skip if it's already print(...) or just "print"
        if re.match(r'^\s*print\s*\(', line) or re.match(r'^\s*print\s*$', line):
            fixed_lines.append(line)
            continue
            
        # Check for print statement
        match = re.match(print_pattern, line)
        if match:
            indent = match.group(1)
            content = match.group(2).rstrip()
            
            # Remove trailing comma if present (Python 2 print with comma)
            if content.endswith(','):
                content = content[:-1].rstrip()
                fixed_line = f"{indent}print({content}, end=' ')"
            else:
                fixed_line = f"{indent}print({content})"
            
            fixed_lines.append(fixed_line)
            changes.append(f"Line {i+1}: print statement → print()")
        else:
            fixed_lines.append(line)
    
    new_code = '\n'.join(fixed_lines)
    
    return new_code, changes


def process_file(path: Path) -> FileResult:
    """Process a single Python file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        
        # Handle empty files
        if not code.strip():
            return {
                "file": str(path),
                "code": code,
                "changes": [],
                "status": "skipped_empty"
            }
        
        new_code, changes = safe_replace_tokens(code)
        
        return {
            "file": str(path),
            "code": new_code,
            "changes": changes,
            "status": "success"
        }
        
    except Exception as e:
        # If processing fails, return original code
        return {
            "file": str(path),
            "code": code if 'code' in locals() else "",
            "changes": [],
            "status": "error",
            "error": str(e)
        }


def preprocess_repo(src_dir: Path, out_dir: Path) -> List[FileResult]:
    """
    Preprocess all .py files from src_dir into out_dir.
    Writes stage0_metadata.json.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for py_file in src_dir.rglob("*.py"):
        res = process_file(py_file)
        results.append(res)

        # Write processed file
        relative_path = py_file.relative_to(src_dir)
        target_path = out_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(res["code"])

    # Write metadata
    metadata_path = out_dir / "stage0_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(
            [{
                "file": r["file"], 
                "changes": r["changes"],
                "status": r.get("status", "unknown")
            } for r in results], 
            f, 
            indent=4
        )

    return results


# --- Simple test ---
if __name__ == "__main__":
    src = Path("./sample_repo")
    out = Path("./sessions/test_session/stage0_preprocessed")
    res = preprocess_repo(src, out)
    print(f"Processed {len(res)} files. Metadata at {out / 'stage0_metadata.json'}")
    
    # Show summary
    for r in res:
        if r.get("changes"):
            print(f"\n{r['file']}:")
            for change in r['changes']:
                print(f"  - {change}")