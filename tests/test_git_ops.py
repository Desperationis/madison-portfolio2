"""Tests for gui.git_ops module."""

from unittest.mock import patch, MagicMock
import subprocess

from gui.git_ops import check_git_status, get_deploy_preflight, deploy, _run_git


def test_run_git_status():
    """_run_git can execute 'git status' and return a CompletedProcess."""
    result = _run_git("status")
    assert result.returncode == 0


def test_check_git_status_returns_all_keys():
    """check_git_status returns a dict with all expected keys."""
    status = check_git_status()
    expected_keys = {
        "git_available",
        "is_repo",
        "has_remote",
        "remote_url",
        "branch",
        "has_uncommitted",
        "has_unpushed",
    }
    assert set(status.keys()) == expected_keys


def test_check_git_status_values():
    """check_git_status returns reasonable values for this repo."""
    status = check_git_status()
    assert status["git_available"] is True
    assert status["is_repo"] is True
    assert isinstance(status["branch"], str)
    assert len(status["branch"]) > 0
    assert isinstance(status["has_uncommitted"], bool)
    assert isinstance(status["has_unpushed"], bool)


def test_get_deploy_preflight_ready():
    """get_deploy_preflight returns ready=True on this repo."""
    result = get_deploy_preflight()
    assert set(result.keys()) == {"ready", "errors", "warnings"}
    assert result["ready"] is True
    assert isinstance(result["errors"], list)
    assert len(result["errors"]) == 0
    assert isinstance(result["warnings"], list)


def _mock_run_side_effect(cmd, **kwargs):
    """Return a successful CompletedProcess for any subprocess.run call."""
    stdout = ""
    if cmd[0] == "git":
        if cmd[1:3] == ["status", "--porcelain"]:
            stdout = "M config.yaml\n"
        elif cmd[1:3] == ["rev-parse", "--abbrev-ref"]:
            stdout = "main\n"
        elif cmd[1] == "commit":
            stdout = "[main abc1234] Update portfolio\n"
        elif cmd[1] == "pull":
            stdout = "Already up to date.\n"
        elif cmd[1] == "push":
            stdout = "Everything up-to-date\n"
    return subprocess.CompletedProcess(cmd, returncode=0, stdout=stdout, stderr="")


def test_deploy_all_steps_succeed():
    """deploy() with all subprocess calls succeeding returns success with 6 steps."""
    with patch("gui.git_ops.subprocess.run", side_effect=_mock_run_side_effect):
        result = deploy("Test deploy")

    assert result["success"] is True
    assert result["error"] is None
    assert len(result["steps"]) == 6
    for step in result["steps"]:
        assert step["success"] is True
        assert step["skipped"] is False
        assert step["error"] is None


def test_deploy_push_failure():
    """deploy() when git push fails: steps 1-5 succeed, step 6 fails."""
    call_count = {"n": 0}

    def side_effect(cmd, **kwargs):
        call_count["n"] += 1
        # Make git push fail
        if cmd[0] == "git" and cmd[1] == "push":
            return subprocess.CompletedProcess(
                cmd, returncode=1, stdout="", stderr="Permission denied (publickey)."
            )
        return _mock_run_side_effect(cmd, **kwargs)

    with patch("gui.git_ops.subprocess.run", side_effect=side_effect):
        result = deploy("Test deploy")

    assert result["success"] is False
    assert result["error"] is not None
    assert "Permission denied" in result["error"]
    assert len(result["steps"]) == 6
    # Steps 1-5 succeed
    for step in result["steps"][:5]:
        assert step["success"] is True
    # Step 6 fails
    assert result["steps"][5]["name"] == "Pushing"
    assert result["steps"][5]["success"] is False


def test_deploy_generator_failure():
    """deploy() when site generation fails: only step 1 runs and fails, rest skipped."""
    def side_effect(cmd, **kwargs):
        # Make portfolio generation fail
        if cmd[0] != "git":
            return subprocess.CompletedProcess(
                cmd, returncode=1, stdout="", stderr="ModuleNotFoundError: No module named 'portfolio'"
            )
        return _mock_run_side_effect(cmd, **kwargs)

    with patch("gui.git_ops.subprocess.run", side_effect=side_effect):
        result = deploy("Test deploy")

    assert result["success"] is False
    assert "ModuleNotFoundError" in result["error"]
    assert len(result["steps"]) == 6
    # Step 1 failed
    assert result["steps"][0]["name"] == "Generating site"
    assert result["steps"][0]["success"] is False
    # Remaining steps skipped
    for step in result["steps"][1:]:
        assert step["skipped"] is True
