from __future__ import annotations

import json
from pathlib import Path

import pytest

from rec_frame_agent.capabilities import build_capabilities
from rec_frame_agent.cli import main
from rec_frame_agent.errors import AgentError
from rec_frame_agent.presets import create_preset, resolve_preset
from rec_frame_agent.runner import apply


def _run(capsys, argv) -> tuple[int, dict]:
    code = main(argv)
    return code, json.loads(capsys.readouterr().out)


def test_capabilities_axes_match_engine():
    caps = build_capabilities()
    axes = caps["axes"]
    assert "green" in axes["color"]["presets"]
    assert len(axes["font"]["bundled"]) == 6
    assert "glow_red" in axes["dot_style"]["choices"]
    assert caps["presets"]["current"]["resolved"] == "ai-photo-white"


def test_create_preset_with_base_diff():
    report = create_preset(
        "my-dseg", {"font_key": "DSEG7 Classic(7セグLED)", "custom_color": "cyan", "color": "white"},
        base_name="favorite",
    )
    assert report["base"] == "ai-photo-white"
    r = resolve_preset("my-dseg")
    assert r.raw["font_key"].startswith("DSEG7")
    assert r.raw["battery_bars"] == 3  # base から継承
    assert r.timecode_mode == "processed_at"  # base から継承


def test_create_preset_duplicate_and_overwrite():
    create_preset("dup", {"color": "black"})
    with pytest.raises(AgentError) as e:
        create_preset("dup", {"color": "white"})
    assert e.value.exit_code == 4
    create_preset("dup", {"color": "white"}, overwrite=True)
    assert resolve_preset("dup").raw["color"] == "white"


def test_create_preset_invalid_font_rejected():
    with pytest.raises(AgentError) as e:
        create_preset("bad", {"font_key": "存在しないフォント"})
    assert e.value.exit_code == 2


def test_create_preset_reserved_name_rejected():
    with pytest.raises(AgentError):
        create_preset("favorite", {"color": "black"})


def test_create_and_favorite_then_apply(sample_image, capsys):
    code, data = _run(capsys, [
        "presets", "--json", "create", "night-blue",
        "--base", "favorite", "--color", "cyan", "--favorite",
    ])
    assert code == 0 and data["favorite"] is True
    report = apply(str(sample_image), at_text="2026-11-03T21:05")
    assert report["preset_resolved"] == "night-blue"
    assert Path(report["output"]).is_file()


def test_capabilities_cli(capsys):
    code, data = _run(capsys, ["capabilities", "--json"])
    assert code == 0 and data["ok"] is True
