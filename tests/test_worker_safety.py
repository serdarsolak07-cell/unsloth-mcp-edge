import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "mcp-worker"))
sys.path.insert(0, str(Path(__file__).parents[1] / "mcp-host"))
from main_host import configured_tool_round_limit
from tools.operations import WorkerOperations
from tools.safety import SafetyError, checked_command, checked_path


def test_checked_path_rejects_protected(tmp_path):
    protected = tmp_path / "secret"
    protected.mkdir()
    with pytest.raises(SafetyError):
        checked_path(str(protected / "x"), [tmp_path], [protected])


def test_checked_command_rejects_shell_operators():
    with pytest.raises(SafetyError):
        checked_command("ls; rm -rf /", {"ls", "rm"})


def test_checked_command_accepts_arguments():
    assert checked_command("ls -la", {"ls"}) == ["ls", "-la"]


def test_worker_runs_in_allowed_root_and_supports_development_commands(tmp_path):
    ops = WorkerOperations({"allowed_paths": [str(tmp_path)]})
    assert "exit=0" in ops.command("python3 -c 'print(123)'")


def test_remove_recursively_deletes_directory(tmp_path):
    nested = tmp_path / "project" / "src"
    nested.mkdir(parents=True)
    (nested / "main.py").write_text("print(1)", encoding="utf-8")
    ops = WorkerOperations({"allowed_paths": [str(tmp_path)]})
    ops.remove(str(tmp_path / "project"))
    assert not (tmp_path / "project").exists()


def test_copy_and_move_support_directories(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "file.txt").write_text("ok", encoding="utf-8")
    ops = WorkerOperations({"allowed_paths": [str(tmp_path)]})
    copied = Path(ops.copy(str(source), str(tmp_path / "copy")))
    assert (copied / "file.txt").read_text(encoding="utf-8") == "ok"
    moved = Path(ops.move(str(copied), str(tmp_path / "moved")))
    assert (moved / "file.txt").exists() and not copied.exists()


def test_command_output_is_bounded(tmp_path):
    ops = WorkerOperations({
        "allowed_paths": [str(tmp_path)],
        "max_command_output_bytes": 32,
    })
    result = ops.command("python3 -c 'print(\"x\" * 1000)'")
    assert "[output truncated]" in result


def test_tool_rounds_are_unlimited_by_default():
    assert configured_tool_round_limit({"max_tool_rounds": None}) is None
    assert configured_tool_round_limit({}) is None


def test_tool_rounds_can_be_explicitly_bounded():
    assert configured_tool_round_limit({"max_tool_rounds": 12}) == 12
