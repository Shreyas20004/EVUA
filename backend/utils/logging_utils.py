 # write logs + metadata.json

from pathlib import Path
import json
from typing import Any, Dict, List
from utils import file_ops

METADATA_FILENAME = "metadata.json"

# -----------------------------
# Logging Helpers
# -----------------------------

def log_stage(session_dir: Path, stage_name: str, data: Dict[str, Any]) -> None:
    """
    Append stage info to session metadata.
    
    Args:
        session_dir: Path to the session folder
        stage_name: Name of the stage
        data: Dict containing stage info (status, result_count, output_dir, etc.)
    """
    session_dir = Path(session_dir)
    metadata_path = session_dir / METADATA_FILENAME

    # Load existing metadata if exists
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    else:
        metadata = {
            "session_id": session_dir.name,
            "stages": [],
            "status": "running"
        }

    # Append new stage info
    stage_entry = {"stage": stage_name, **data}
    metadata.setdefault("stages", []).append(stage_entry)

    # Write metadata atomically
    file_ops.write_json_atomic(metadata_path, metadata)


def read_metadata(session_dir: Path) -> Dict[str, Any]:
    """
    Read session metadata from metadata.json.
    
    Args:
        session_dir: Path to session folder
    
    Returns:
        metadata dict
    """
    metadata_path = Path(session_dir) / METADATA_FILENAME
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    return json.loads(metadata_path.read_text(encoding="utf-8"))
