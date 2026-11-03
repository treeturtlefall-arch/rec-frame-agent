from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from rec_frame_agent.engine import ENGINE_DIR, load as load_engine
from rec_frame_agent.presets import resolve_preset
from rec_frame_agent.runner import apply

rec_config, rec_overlay, rec_batch = load_engine()


def test_engine_files_unmodified():
    """同梱エンジンがマニフェストの SHA-256 と一致する（改変なしの担保）。"""
    manifest = json.loads(
        (Path(__file__).resolve().parents[1] / "src" / "rec_frame_agent" / "data" / "engine_hashes.json")
        .read_text(encoding="utf-8")
    )
    assert manifest
    for name, want in manifest.items():
        got = hashlib.sha256((ENGINE_DIR / name).read_bytes()).hexdigest()
        assert got == want, name


def test_apply_matches_engine_directly(sample_image, tmp_path):
    """runner 経由の出力が、本家 process_single_file の直接実行とピクセル一致する。"""
    resolved = resolve_preset("classic-black")
    cfg = rec_config.OverlayConfig.from_dict(resolved.config_dict())
    expected = tmp_path / "expected.png"
    rec_batch.process_single_file(sample_image, expected, cfg)

    report = apply(str(sample_image), preset_name="classic-black")
    got_img = Image.open(report["output"]).convert("RGBA")
    exp_img = Image.open(expected).convert("RGBA")
    assert got_img.size == exp_img.size
    assert got_img.tobytes() == exp_img.tobytes()


def test_processed_at_is_deterministic_when_frozen(sample_image, tmp_path):
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    apply(str(sample_image), output=str(a), at_text="2026-11-03T14:30")
    apply(str(sample_image), output=str(b), at_text="2026-11-03T14:30", overwrite=True)
    assert Image.open(a).convert("RGBA").tobytes() == Image.open(b).convert("RGBA").tobytes()
