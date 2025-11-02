import uuid
from pathlib import Path
from datetime import datetime

from core.languages.python import pipeline
from utils import file_ops 
from utils import logging_utils  # optional logging


def run_pipeline(repo_path: Path, language: str = "python", max_attempts: int = 3) -> Path:
    """
    Language-agnostic orchestrator: triggers the appropriate language pipeline.

    Args:
        repo_path (Path): Path to the source repository.
        language (str): Which language adapter to use.
        max_attempts (int): Maximum number of automated repair attempts.

    Returns:
        Path: Session directory where outputs and metadata are stored.
    """
    sessions_dir = Path("./sessions")
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique session ID
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    session_id = f"{language}_{timestamp}_{uuid.uuid4().hex[:6]}"
    session_dir = sessions_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ✅ Prepare config for language pipeline
        config = {"max_attempts": max_attempts}

        if language.lower() == "python":
            # ✅ Removed invalid `max_attempts` argument
            metadata = pipeline.run_pipeline(
                repo_path=repo_path,
                session_dir=session_dir,
                config=config,
            )
        else:
            raise NotImplementedError(f"Language not supported: {language}")

        file_ops.write_json_atomic(session_dir / "metadata.json", metadata)
        print(f"✅ Pipeline completed successfully for session {session_id}")

    except Exception as e:
        print(f"Pipeline failed for session {session_id}: {e}")
        import traceback
        fail_meta = {
            "session_id": session_id,
            "language": language,
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "start_time": datetime.utcnow().isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "stages": [],
        }
        file_ops.write_json_atomic(session_dir / "metadata.json", fail_meta)

    return session_dir
