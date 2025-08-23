import os
import subprocess
import sys
import tempfile

# Avoid permission issues with modernize cache
os.environ["XDG_CACHE_HOME"] = os.path.expanduser("~/.cache")

def upgrade_file(src_path, dest_path):
    """
    Upgrade a single Python file using `modernize` and save to dest_path.
    """
    # Read original source code
    with open(src_path, "r", encoding="utf-8") as f:
        original_code = f.read()

    # Create temporary file for in-place modernize conversion
    with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(original_code)
        tmp_path = tmp.name

    # Run modernize
    result = subprocess.run(
        [sys.executable, "-m", "modernize", "-w", tmp_path],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        os.remove(tmp_path)
        raise RuntimeError(f"modernize failed: {result.stderr}")

    # Read upgraded code
    with open(tmp_path, "r", encoding="utf-8") as f:
        upgraded_code = f.read()

    os.remove(tmp_path)

    # Ensure destination directory exists
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    # Write upgraded code
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(upgraded_code)

    print(f"Upgraded: {dest_path}")
