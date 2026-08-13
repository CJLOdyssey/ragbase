"""Tests for _kill_stuck_child_processes (agent_pipeline child cleanup)."""

from unittest.mock import MagicMock, mock_open, patch

from tasks.agent_pipeline import _kill_stuck_child_processes


def test_kills_multiprocessing_spawn_children():
    """Child whose cmdline contains multiprocessing.spawn is killed."""
    pipe = MagicMock()
    pipe.__enter__.return_value = pipe
    pipe.stdout.read.return_value = "123\n"
    with (
        patch("tasks.agent_pipeline.subprocess.Popen", return_value=pipe) as popen,
        patch("tasks.agent_pipeline.open", mock_open(read_data="/usr/bin/python\0-m\0multiprocessing.spawn\0")),
        patch("tasks.agent_pipeline.os.kill") as m_kill,
        patch("tasks.agent_pipeline.os.getpid", return_value=999),
    ):
        _kill_stuck_child_processes()

    popen.assert_called_once()
    assert popen.call_args.args[0] == ["ps", "--ppid", "999", "-o", "pid=", "--no-headers"]
    m_kill.assert_called_once_with(123, 9)


def test_skips_non_spawn_and_missing_proc():
    """Non-spawn children and missing /proc entries are ignored."""
    pipe = MagicMock()
    pipe.__enter__.return_value = pipe
    pipe.stdout.read.return_value = "1\n2\n"

    def _fake_open(path, *a, **kw):
        if path == "/proc/1/cmdline":
            return mock_open(read_data="/usr/bin/python\0-u\0worker.py\0")()
        raise FileNotFoundError(path)

    with (
        patch("tasks.agent_pipeline.subprocess.Popen", return_value=pipe),
        patch("tasks.agent_pipeline.open", side_effect=_fake_open),
        patch("tasks.agent_pipeline.os.kill") as m_kill,
    ):
        _kill_stuck_child_processes()
    m_kill.assert_not_called()


def test_cleanup_failure_is_swallowed():
    """Popen itself failing (no ps on PATH) must not propagate."""
    with patch("tasks.agent_pipeline.subprocess.Popen", side_effect=OSError("no ps")):
        _kill_stuck_child_processes()
