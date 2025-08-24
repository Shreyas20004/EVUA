#use: Go to backend folder and run
#python core/parser.py upgrade --src source folder location --dst destination folder location
#Ex: python core/parser.py upgrade --src projects/source --dst projects/destination

import os
import shutil
import subprocess
from pathlib import Path
import argparse
from pyParser import upgrade_file as upgrade_python

# --- JS upgrader wrapper ---
def upgrade_js(src, dst):
    try:
        subprocess.run(
            ["node", os.path.join(os.path.dirname(__file__), "jsParser.mjs"), src, dst],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Upgraded JS: {src} → {dst}")
    except subprocess.CalledProcessError as e:
        print(f"Error upgrading JS {src}: {e.stderr}")
        # fallback: just copy file
        shutil.copy2(src, dst)
        print(f"Copied (fallback): {src}")

# Map file extensions to language-specific upgrade functions
LANG_UPGRADERS = {
    ".py": upgrade_python,
    ".js": upgrade_js,
    # future: ".java": upgrade_java,
}

def detect_language(file_path):
    ext = Path(file_path).suffix.lower()
    return LANG_UPGRADERS.get(ext)

def is_python2_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if "print " in line or "xrange" in line or "raw_input(" in line:
                    return True
    except Exception:
        return False
    return False

def parse_and_upgrade(source_path, dest_path):
    """
    Upgrade files in source_path and save them to dest_path.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source path not found: {source_path}")

    # If source_path is a single file
    if os.path.isfile(source_path):
        upgrader = detect_language(source_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        if upgrader:
            if source_path.endswith(".py") and is_python2_file(source_path):
                upgrader(source_path, dest_path)
            elif source_path.endswith(".js"):
                upgrader(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)
                print(f"Copied (up-to-date): {source_path}")
        else:
            shutil.copy2(source_path, dest_path)
            print(f"Copied (non-upgradeable): {source_path}")
        return

    # If source_path is a folder
    for root, _, files in os.walk(source_path):
        for file in files:
            src_file = os.path.join(root, file)
            rel_path = os.path.relpath(src_file, source_path)
            dst_file = os.path.join(dest_path, rel_path)

            upgrader = detect_language(src_file)
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)

            if upgrader:
                if file.endswith(".py") and is_python2_file(src_file):
                    upgrader(src_file, dst_file)
                elif file.endswith(".js"):
                    upgrader(src_file, dst_file)
                else:
                    shutil.copy2(src_file, dst_file)
                    print(f"Copied (Python3 or up-to-date): {rel_path}")
            else:
                shutil.copy2(src_file, dst_file)
                print(f"Copied (non-upgradeable): {rel_path}")

def main():
    parser = argparse.ArgumentParser(description="Multi-language project upgrader CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade a project or file")
    upgrade_parser.add_argument("--src", required=True, help="Source file or folder")
    upgrade_parser.add_argument("--dst", required=True, help="Destination folder")

    args = parser.parse_args()

    if args.command == "upgrade":
        src_path = os.path.abspath(args.src)
        dst_path = os.path.abspath(args.dst)
        print(f"Upgrading from {src_path} → {dst_path}")
        parse_and_upgrade(src_path, dst_path)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
