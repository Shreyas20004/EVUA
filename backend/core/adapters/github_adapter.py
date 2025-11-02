import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import tempfile


@dataclass
class RepoInfo:
    repo_path: Path
    branch_name: str
    base_branch: str = "main"
    remote: str = "origin"
    github_url: Optional[str] = None


def _run_git_command(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    """Safely execute a git command and capture output."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def create_patch_branch(session_dir: Path, files_to_commit: List[Path], repo_info: RepoInfo) -> str:
    """
    Creates a new git branch, commits the given files, and prepares a patch/PR.
    For MVP, generates a .patch file locally. Optionally constructs a PR URL.
    """
    repo = repo_info.repo_path
    if not (repo / ".git").exists():
        raise RuntimeError(f"{repo} is not a valid git repository")

    branch = repo_info.branch_name

    # Create and checkout new branch
    _run_git_command(["checkout", repo_info.base_branch], cwd=repo)
    _run_git_command(["pull", repo_info.remote, repo_info.base_branch], cwd=repo)
    _run_git_command(["checkout", "-b", branch], cwd=repo)

    # Copy changed files into repo
    for file in files_to_commit:
        target = repo / file.name
        if file != target:
            target.write_bytes(file.read_bytes())

    # Stage and commit
    rel_files = [f.name for f in files_to_commit]
    _run_git_command(["add"] + rel_files, cwd=repo)
    _run_git_command(["commit", "-m", f"EVUA: automated patch for {branch}"], cwd=repo)

    # Create patch file
    patch_file = session_dir / f"{branch}.patch"
    result = _run_git_command(["format-patch", "-1", "--stdout"], cwd=repo)
    patch_file.write_text(result.stdout, encoding="utf-8")

    # Construct optional PR URL (mock for MVP)
    pr_url = f"{repo_info.github_url}/compare/{repo_info.base_branch}...{branch}" if repo_info.github_url else str(patch_file)

    return pr_url
