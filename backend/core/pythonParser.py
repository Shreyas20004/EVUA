import os
import subprocess
import shutil
import sys
import tempfile

# Avoid permission issues with modernize cache
os.environ["XDG_CACHE_HOME"] = os.path.expanduser("~/.cache")

# Upgrade a single Python file using the `modernize` tool
def upgrade_single_file(file_path):
    # Read original source code
    with open(file_path, "r", encoding="utf-8") as f:
        original_code = f.read()

    # Create a temporary file to apply in-place conversion
    with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(original_code)
        tmp_path = tmp.name

    # Run `modernize` tool in-place on the temp file
    result = subprocess.run(
        [sys.executable, "-m", "modernize", "-w", tmp_path],
        capture_output=True,
        text=True,
    )

    # Handle failure and clean up
    if result.returncode != 0:
        os.remove(tmp_path)
        raise RuntimeError(f"modernize failed: {result.stderr}")

    # Read back upgraded code from the temp file
    with open(tmp_path, "r", encoding="utf-8") as f:
        upgraded_code = f.read()

    os.remove(tmp_path) # Clean up temp file
    return upgraded_code

#Upgrade an entire Python 2 project to Python 3
def upgrade_project(original_dir, converted_dir):
    # Validate input folder exists
    if not os.path.exists(original_dir):
        raise FileNotFoundError(f"Original directory not found: {original_dir}")

    # If output folder exists, delete and recreate it
    if os.path.exists(converted_dir):
        shutil.rmtree(converted_dir)
    os.makedirs(converted_dir)

    # Walk through the original project directory
    for root, _, files in os.walk(original_dir):
        for file in files:
            orig_file_path = os.path.join(root, file)
            relative_path = os.path.relpath(orig_file_path, original_dir)
            new_file_path = os.path.join(converted_dir, relative_path)

            # Ensure parent directories exist in destination
            os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

            if file.endswith(".py"):
                # Try to upgrade Python files
                try:
                    upgraded_code = upgrade_single_file(orig_file_path)
                    with open(new_file_path, "w", encoding="utf-8") as f:
                        f.write(upgraded_code)
                    print(f"Upgraded: {relative_path}")
                except Exception as e:
                    print(f"Failed to upgrade {orig_file_path}: {e}")
            else:
                shutil.copy2(orig_file_path, new_file_path)
                print(f"Copied (non-Python): {relative_path}")

#Entry point: Accept folder arguments and trigger upgrade
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python upgrade.py <original_folder> <converted_folder>")
        sys.exit(1)

    # Resolve absolute paths for clarity and robustness
    original_path = os.path.abspath(sys.argv[1])
    converted_path = os.path.abspath(sys.argv[2])

    print("Original Folder:", original_path)
    print("Converted Folder:", converted_path)

    # Start upgrading project
    upgrade_project(original_path, converted_path)
