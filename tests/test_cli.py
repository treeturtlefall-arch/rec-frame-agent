from __future__ import annotations

import json

from rec_frame_agent.agentfonts import AGENT_FONTS, list_agent_fonts
from rec_frame_agent.capabilities import build_capabilities
from rec_frame_agent.presets import create_preset, user_presets_dir
from rec_frame_agent.runner import apply


# ---- エージェント同梱フォント（DESIGN.md §17.4） ----

def test_agent_fonts_listed():
    fonts = list_agent_fonts()
    assert set(fonts) == set(AGENT_FONTS)
    assert any("DSEG14" in n for n in fonts)
    assert any("Audiowide" in n for n in fonts)


def test_apply_with_agent_font(sample_image, isolated_user_config):
    name = next(n for n in AGENT_FONTS if "DSEG14" in n)
    create_preset("seg14", {"font_key": name})
    report = apply(str(sample_image), preset_name="seg14")
    assert report["ok"] is True
    saved = json.loads((user_presets_dir() / "seg14.json").read_text(encoding="utf-8"))
    assert saved["font_key"] == name
    assert str(isolated_user_config) not in json.dumps(saved)  # 絶対パスを持たない


def test_capabilities_include_agent_fonts():
    axes = build_capabilities()["axes"]
    assert any("DSEG14" in n for n in axes["font"]["agent_bundled"])
    assert any("Audiowide" in n for n in axes["font"]["agent_bundled"])
