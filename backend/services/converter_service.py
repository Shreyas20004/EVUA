# backend/services/converter_service.py

from pathlib import Path
import shutil
import uuid
from datetime import datetime

from core.engine import controller
from utils import file_ops

# Directory where all sessions are stored
SESSIONS_DIR = Path("./sessions")

def start_conversion(uploaded_archive: Path, language: str, user_id: str) -> str:
    """
    Handles the conversion request from the user.

    Steps:
    1. Creates a new session directory.
    2. Extracts / copies the uploaded archive into the session.
    3. Calls the language-agnostic controller to run the conversion.
    4. Returns the session_id.

    Args:
        uploaded_archive (Path): Path to the uploaded project archive (zip, tar, etc.).
        language (str): Target language, e.g., "python".
        user_id (str): ID of the user requesting conversion.

    Returns:
        session_id (str): Unique session identifier for tracking conversion.
    """
    # Ensure sessions directory exists
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate a unique session ID
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    session_id = f"{language}_{timestamp}_{uuid.uuid4().hex[:6]}"
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Copy or extract uploaded archive into 'originals' folder
    originals_dir = session_dir / "originals"
    originals_dir.mkdir(exist_ok=True)
    if uploaded_archive.is_file() and uploaded_archive.suffix in {".zip", ".tar", ".gz"}:
        # Use file_ops helper to extract archive
        file_ops.extract_archive(uploaded_archive, originals_dir)
    else:
        # If folder, just copy
        if uploaded_archive.is_dir():
            shutil.copytree(uploaded_archive, originals_dir, dirs_exist_ok=True)
        else:
            # Single file, just copy it
            shutil.copy2(uploaded_archive, originals_dir)

    # Prepare session config for the controller
    session_config = {
        "repo_path": originals_dir,
        "language": language,
        "sessions_dir": SESSIONS_DIR,
        "config": {}  # Add docker image, timeout, etc. if needed
    }

    # Run the language pipeline
    controller.run(session_config)

    return session_id
