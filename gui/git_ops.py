"""Git status checks, preflight validation, and deploy pipeline."""

import logging
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_git(*args: str, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run a git command and return the CompletedProcess result."""
    cmd = ["git", *args]
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("Git command timed out after %ds: git %s", timeout, ' '.join(args))
        raise RuntimeError(
            f"Git command timed out after {timeout}s: git {' '.join(args)}"
        ) from exc


def sync_to_origin() -> None:
    """Force-sync the local repo to match origin, discarding all local changes.

    Runs: git fetch origin → git reset --hard origin/<branch> → git clean -fd.
    Raises RuntimeError if any step fails.
    """
    if shutil.which("git") is None:
        raise RuntimeError("git is not installed or not on PATH")

    # Must be inside a repo
    proc = _run_git("rev-parse", "--is-inside-work-tree")
    if proc.returncode != 0:
        raise RuntimeError("Not a git repository")

    # Determine current branch
    proc = _run_git("rev-parse", "--abbrev-ref", "HEAD")
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError("Cannot determine current branch (detached HEAD?)")
    branch = proc.stdout.strip()

    # Fetch latest from origin
    logger.info("Fetching origin...")
    proc = _run_git("fetch", "origin", timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(f"git fetch origin failed: {proc.stderr}")

    # Hard reset to origin/<branch>
    logger.info("Resetting to origin/%s...", branch)
    proc = _run_git("reset", "--hard", f"origin/{branch}")
    if proc.returncode != 0:
        raise RuntimeError(f"git reset --hard failed: {proc.stderr}")

    # Remove untracked files/dirs
    logger.info("Cleaning untracked files...")
    proc = _run_git("clean", "-fd")
    if proc.returncode != 0:
        raise RuntimeError(f"git clean -fd failed: {proc.stderr}")

    logger.info("Synced to origin/%s", branch)


def check_git_status() -> dict:
    """Return a dict describing the current git repository status."""
    result = {
        "git_available": False,
        "is_repo": False,
        "has_remote": False,
        "remote_url": None,
        "branch": None,
        "has_uncommitted": False,
        "has_unpushed": False,
    }

    # git_available
    result["git_available"] = shutil.which("git") is not None
    if not result["git_available"]:
        return result

    # is_repo
    proc = _run_git("rev-parse", "--is-inside-work-tree")
    result["is_repo"] = proc.returncode == 0
    if not result["is_repo"]:
        return result

    # has_remote / remote_url
    proc = _run_git("remote", "get-url", "origin")
    if proc.returncode == 0:
        result["has_remote"] = True
        result["remote_url"] = proc.stdout.strip()

    # branch
    proc = _run_git("rev-parse", "--abbrev-ref", "HEAD")
    if proc.returncode == 0:
        result["branch"] = proc.stdout.strip()

    # has_uncommitted
    proc = _run_git("status", "--porcelain")
    if proc.returncode == 0:
        result["has_uncommitted"] = bool(proc.stdout.strip())

    # has_unpushed
    proc = _run_git("log", "@{u}..HEAD", "--oneline")
    if proc.returncode == 0:
        result["has_unpushed"] = bool(proc.stdout.strip())
    # If no upstream is set, returncode != 0 — treat as no unpushed info

    return result


def get_deploy_preflight() -> dict:
    """Check whether the repo is ready to deploy.

    Returns a dict with keys:
        ready (bool): True if no errors were found.
        errors (list[str]): Blocking problems that prevent deploy.
        warnings (list[str]): Non-blocking issues worth noting.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check: git is available
    if shutil.which("git") is None:
        errors.append("git is not installed or not on PATH")
        return {"ready": False, "errors": errors, "warnings": warnings}

    # Check: is a git repo
    proc = _run_git("rev-parse", "--is-inside-work-tree")
    if proc.returncode != 0:
        errors.append("Not a git repository")
        return {"ready": False, "errors": errors, "warnings": warnings}

    # Check: remote "origin" exists
    proc = _run_git("remote", "get-url", "origin")
    if proc.returncode != 0:
        errors.append('No remote "origin" configured')

    # Check: not in a rebase/merge state
    git_dir = PROJECT_ROOT / ".git"
    if (git_dir / "rebase-merge").exists() or (git_dir / "MERGE_HEAD").exists():
        errors.append(
            "Repository is in a rebase or merge state — resolve it before deploying"
        )

    # Check: not in detached HEAD
    proc = _run_git("symbolic-ref", "HEAD")
    if proc.returncode != 0:
        errors.append("HEAD is detached — check out a branch before deploying")

    # Check: can reach remote (warning only, not blocking)
    try:
        proc = _run_git("ls-remote", "--exit-code", "origin", "HEAD", timeout=15)
        if proc.returncode != 0:
            warnings.append("Cannot reach remote — network may be unavailable")
    except RuntimeError:
        warnings.append("Remote connectivity check timed out — network may be unavailable")

    if errors:
        logger.error("Deploy preflight failed: %s", errors)
    else:
        logger.info("Deploy preflight passed")
    return {"ready": len(errors) == 0, "errors": errors, "warnings": warnings}


def _make_step(name: str, *, success: bool = False, output: str = "",
               error: str | None = None, skipped: bool = False) -> dict:
    """Create a step result dict."""
    return {
        "name": name,
        "success": success,
        "output": output,
        "error": error,
        "skipped": skipped,
    }


def deploy(commit_message: str = "Update portfolio") -> dict:
    """Run the full deploy pipeline: pull → generate → stage → commit → push.

    Returns a dict with keys:
        success (bool): True if all steps completed successfully.
        steps (list[dict]): One dict per step with keys name, success, output, error, skipped.
        error (str | None): Top-level error message, or None on success.
    """
    step_names = [
        "Pulling latest",
        "Generating site",
        "Staging changes",
        "Checking for changes",
        "Committing",
        "Pushing",
    ]
    steps: list[dict] = []

    def _fail(step: dict, error_msg: str) -> dict:
        """Mark current step as failed and remaining steps as skipped."""
        logger.error("Deploy failed at '%s': %s", step["name"], error_msg)
        step["success"] = False
        step["error"] = error_msg
        # Add skipped entries for remaining steps
        completed_names = {s["name"] for s in steps}
        for name in step_names:
            if name not in completed_names:
                steps.append(_make_step(name, skipped=True))
        return {"success": False, "steps": steps, "error": error_msg}

    logger.info("Starting deploy with message: %s", commit_message)

    # Step 1: Pull latest
    step = _make_step("Pulling latest")
    steps.append(step)
    branch_proc = _run_git("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else "main"
    try:
        proc = _run_git("pull", "--rebase", "origin", branch, timeout=30)
        step["output"] = proc.stdout
        if proc.returncode != 0:
            error_msg = (proc.stderr or "Failed to pull latest changes") + \
                "\nTry running `git rebase --abort` to undo, then resolve conflicts manually."
            return _fail(step, error_msg)
        step["success"] = True
    except RuntimeError as exc:
        return _fail(step, str(exc))

    # Step 2: Generate site
    step = _make_step("Generating site")
    steps.append(step)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "portfolio"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=PROJECT_ROOT,
        )
        step["output"] = proc.stdout
        if proc.returncode != 0:
            return _fail(step, proc.stderr or "Site generation failed")
        step["success"] = True
    except subprocess.TimeoutExpired:
        return _fail(step, "Site generation timed out after 60s")

    # Step 3: Stage changes
    step = _make_step("Staging changes")
    steps.append(step)
    try:
        proc = _run_git("add", "-A")
        step["output"] = proc.stdout
        if proc.returncode != 0:
            return _fail(step, proc.stderr or "Failed to stage changes")
        step["success"] = True
    except RuntimeError as exc:
        return _fail(step, str(exc))

    # Step 4: Check for changes
    step = _make_step("Checking for changes")
    steps.append(step)
    try:
        proc = _run_git("status", "--porcelain")
        step["output"] = proc.stdout
        if proc.returncode != 0:
            return _fail(step, proc.stderr or "Failed to check status")
        if not proc.stdout.strip():
            step["success"] = True
            step["output"] = "No changes to deploy"
            # Mark remaining steps as skipped
            for name in step_names[4:]:
                steps.append(_make_step(name, skipped=True))
            return {"success": True, "steps": steps, "error": None}
        step["success"] = True
    except RuntimeError as exc:
        return _fail(step, str(exc))

    # Step 5: Commit
    step = _make_step("Committing")
    steps.append(step)
    try:
        proc = _run_git("commit", "-m", commit_message)
        step["output"] = proc.stdout
        if proc.returncode != 0:
            return _fail(step, proc.stderr or "Failed to commit")
        step["success"] = True
    except RuntimeError as exc:
        return _fail(step, str(exc))

    # Step 6: Push
    step = _make_step("Pushing")
    steps.append(step)
    try:
        proc = _run_git("push", "origin", branch, timeout=30)
        step["output"] = proc.stdout
        if proc.returncode != 0:
            return _fail(step, proc.stderr or "Failed to push")
        step["success"] = True
    except RuntimeError as exc:
        return _fail(step, str(exc))

    logger.info("Deploy completed successfully")
    return {"success": True, "steps": steps, "error": None}
