 # safe copy, diffs, path utilities

from pathlib import Path
import shutil
import json
import tempfile
import subprocess
from typing import Any

# -----------------------------
# Session Helpers
# -----------------------------

def init_session(base_sessions_dir: Path) -> Path:
    """
    Creates a new timestamped session directory inside base_sessions_dir.
    
    Returns:
        Path to the new session directory
    """
    base_sessions_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    session_dir = base_sessions_dir / f"session_{timestamp}"
    session_dir.mkdir()
    return session_dir


# -----------------------------
# Repo Helpers
# -----------------------------

def copy_repo(src: Path, dst: Path) -> None:
    """
    Recursively copy a source repo to a destination directory.
    """
    if not src.exists():
        raise FileNotFoundError(f"Source repo not found: {src}")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


# -----------------------------
# JSON Helpers
# -----------------------------

def write_json_atomic(path: Path, obj: Any) -> None:
    """
    Write a JSON object to a file atomically.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tf:
        json.dump(obj, tf, indent=4)
        temp_name = Path(tf.name)
    temp_name.replace(path)


# -----------------------------
# Diff / Patch Helpers
# -----------------------------

def git_patch_from_diff(old: Path, new: Path) -> str:
    """
    Generate a git-style patch diff between two directories.
    Requires 'git' installed.
    
    Returns:
        patch string
    """
    if not old.exists() or not new.exists():
        raise FileNotFoundError("Both old and new paths must exist")
    
    cmd = ["git", "diff", "--no-index", "--patch", str(old), str(new)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def read_json(path: Path) -> dict:
    """
    Safely read JSON from a file.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    import json
    return json.loads(path.read_text(encoding="utf-8"))
