from pathlib import Path

from run_natural_transition_rolling_inference import command, parse_gpu_map, run_dir


def test_parse_gpu_map() -> None:
    assert parse_gpu_map("42:1,44:5") == {42: 1, 44: 5}


def test_base_run_is_reused() -> None:
    output = Path("/tmp/rolling")
    assert "episode-00" in str(run_dir(output, 0, 42))
    assert run_dir(output, 500_000, 42) == output / "prefix-0500ms/seed-42"


def test_command_uses_shifted_t0() -> None:
    value = command(500_000, 42, Path("/tmp/out"))
    assert value[value.index("--t0-us") + 1] == "8458186"
