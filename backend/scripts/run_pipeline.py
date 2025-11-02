#!/usr/bin/env python3
"""
EVUA Pipeline Runner

Purpose:
  Convenience script to run the entire migration + verification pipeline locally.

Usage:
  python scripts/run_pipeline.py --repo /path/to/repo --language python

Behavior:
  - Validates CLI arguments
  - Loads environment/config
  - Dispatches to the central controller (which calls pipeline.run_pipeline)
"""

import sys
import argparse
from pathlib import Path
import logging

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger("evua.pipeline_runner")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)

# -----------------------------------------------------------------------------
# Import Setup
# -----------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from core.engine import controller  # noqa: E402
except ImportError as e:
    logger.error(f"Failed to import EVUA modules. Root: {ROOT_DIR}")
    logger.error(str(e))
    sys.exit(1)

# -----------------------------------------------------------------------------
# CLI Argument Parsing
# -----------------------------------------------------------------------------
def parse_args(argv=None) -> argparse.Namespace:
    """Parse CLI arguments for pipeline execution."""
    parser = argparse.ArgumentParser(
        description="Run the full EVUA conversion pipeline locally."
    )
    parser.add_argument(
        "--repo",
        required=True,
        type=Path,
        help="Path to the source repository to process.",
    )
    parser.add_argument(
        "--language",
        required=True,
        choices=["python", "java", "angularjs"],
        help="Language adapter to use for the migration pipeline.",
    )
    parser.add_argument(
        "--max_attempts",
        type=int,
        default=3,
        help="Maximum number of automated repair attempts (default: 3).",
    )
    return parser.parse_args(argv)

# -----------------------------------------------------------------------------
# Main Runner
# -----------------------------------------------------------------------------
def main() -> None:
    """Main entrypoint for local pipeline execution."""
    args = parse_args()

    repo_path = args.repo.resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        sys.exit(f"[ERROR] Invalid repository path: {repo_path}")

    logger.info("🚀 Starting EVUA pipeline")
    logger.info(f"Repository: {repo_path}")
    logger.info(f"Language: {args.language}")
    logger.info(f"Max Repair Attempts: {args.max_attempts}")

    try:
        session_dir = controller.run_pipeline(
            repo_path=repo_path,
            language=args.language,
            max_attempts=args.max_attempts,
        )
        logger.info("✅ Pipeline completed successfully.")
        logger.info(f"Session directory: {session_dir}")
    except Exception as e:
        logger.exception(f"❌ Pipeline failed with error: {e}")
        sys.exit(1)

# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
