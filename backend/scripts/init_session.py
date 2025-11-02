#!/usr/bin/env python3
"""
CLI helper to create a new session folder.
"""

import argparse
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.utils import file_ops

def main():
    parser = argparse.ArgumentParser(description="Initialize a new EVUA session folder")
    parser.add_argument(
        "--base",
        type=str,
        default="sessions",
        help="Base directory to create session folder in (default: sessions/)"
    )
    args = parser.parse_args()

    base_dir = Path(args.base)
    session_dir = file_ops.init_session(base_dir)
    print(f"Created new session directory: {session_dir}")

if __name__ == "__main__":
    main()
