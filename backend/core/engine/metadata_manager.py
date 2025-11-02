# metadata.json creation / merging

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class SessionMetadata:
    """Aggregated metadata across all EVUA stages."""
    session_name: str
    stages: Dict[str, Dict[str, Any]]
    total_files: int
    completed_stages: int


def _load_json(path: Path) -> Dict[str, Any]:
    """Safely load a JSON file if it exists."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def merge_stage_metadata(session_dir: Path) -> SessionMetadata:
    """
    Collects all *_metadata.json files from stage directories and merges them
    into a unified session-level metadata summary.
    """
    stages_data: Dict[str, Dict[str, Any]] = {}

    # Find all metadata files within the session directory
    for stage_dir in session_dir.glob("stage*_*/"):
        meta_file = stage_dir / f"{stage_dir.name.replace('/', '')}_metadata.json"
        if not meta_file.exists():
            # fallback: match any metadata.json file in this stage folder
            alt = list(stage_dir.glob("*metadata.json"))
            if alt:
                meta_file = alt[0]
            else:
                continue
        stage_key = stage_dir.name
        stages_data[stage_key] = _load_json(meta_file)

    completed = len(stages_data)
    total_files = sum(
        v.get("total", 0) for v in stages_data.values() if isinstance(v, dict)
    )

    metadata = SessionMetadata(
        session_name=session_dir.name,
        stages=stages_data,
        total_files=total_files,
        completed_stages=completed,
    )

    # Persist to session root
    persist_metadata(session_dir, metadata)
    return metadata


def persist_metadata(session_dir: Path, metadata: SessionMetadata) -> None:
    """Writes the merged session metadata to session_dir/session_metadata.json."""
    out_path = session_dir / "session_metadata.json"
    out_path.write_text(
        json.dumps(asdict(metadata), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
