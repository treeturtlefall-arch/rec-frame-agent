from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture(autouse=True)
def isolated_user_config(tmp_path, monkeypatch):
    """ユーザープリセット／favorites が実環境へ漏れないように隔離する。"""
    config_dir = tmp_path / "rec_frame_agent_user_config"
    monkeypatch.setenv("REC_FRAME_AGENT_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return tmp_path


@pytest.fixture()
def sample_image(tmp_path) -> Path:
    p = tmp_path / "sample.png"
    Image.new("RGB", (640, 360), (70, 110, 160)).save(p)
    return p
