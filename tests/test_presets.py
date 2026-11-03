from __future__ import annotations

import json
from pathlib import Path

import pytest

from rec_frame_agent.errors import AgentError
from rec_frame_agent.presets import (
    list_preset_files,
    resolve_preset,
    user_presets_dir,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_favorite_resolves_to_ai_photo_white():
    r = resolve_preset("favorite")
    assert r.resolved_name == "ai-photo-white"
    assert r.timecode_mode == "processed_at"
    assert r.raw["color"] == "white"
    assert r.raw["battery_bars"] == 3


def test_aliases():
    assert resolve_preset("お気に入り").resolved_name == "ai-photo-white"
    assert resolve_preset("classic").resolved_name == "classic-black"


def test_direct_name_and_path(tmp_path):
    assert resolve_preset("classic-black").timecode_mode == "none"
    custom = tmp_path / "mine.json"
    custom.write_text(json.dumps({"color": "white"}), encoding="utf-8")
    r = resolve_preset(str(custom))
    assert r.resolved_name == "mine"


def test_not_found_has_candidates():
    with pytest.raises(AgentError) as e:
        resolve_preset("no-such-preset")
    assert e.value.exit_code == 2
    assert "ai-photo-white" in e.value.extra["candidates"]


def test_user_preset_wins_over_bundled(isolated_user_config):
    d = user_presets_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "ai-photo-white.json").write_text(
        json.dumps({"color": "black", "timecode_mode": "none"}), encoding="utf-8"
    )
    r = resolve_preset("favorite")
    assert r.raw["color"] == "black"
    assert r.path.parent == d


def test_bundled_copies_in_sync():
    """リポジトリ直下の presets/ と favorites.json はパッケージ同梱コピーと一致する。"""
    data = REPO_ROOT / "src" / "rec_frame_agent" / "data"
    for name, _ in list_preset_files():
        top = REPO_ROOT / "presets" / f"{name}.json"
        pkg = data / "presets" / f"{name}.json"
        if top.is_file() and pkg.is_file():
            assert json.loads(top.read_text(encoding="utf-8")) == json.loads(pkg.read_text(encoding="utf-8")), name
    assert json.loads((REPO_ROOT / "favorites.json").read_text(encoding="utf-8")) == json.loads((data / "favorites.json").read_text(encoding="utf-8"))
