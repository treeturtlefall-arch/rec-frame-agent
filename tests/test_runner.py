from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PIL import Image

from rec_frame_agent.errors import AgentError
from rec_frame_agent.runner import apply, batch


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_apply_favorite_with_frozen_time(sample_image):
    before = _hash(sample_image)
    report = apply(str(sample_image), at_text="2026-11-03T14:30")
    out = Path(report["output"])
    assert out.is_file() and out.name == "sample_rec.png"
    assert report["preset_resolved"] == "ai-photo-white"
    assert report["timecode"]["mode"] == "processed_at"
    assert report["timecode"]["text"] == "2026/11/03 PM 02:30"
    assert (report["width"], report["height"]) == (640, 360)
    assert _hash(sample_image) == before  # 元画像は不変


def test_apply_classic_has_no_timecode(sample_image):
    report = apply(str(sample_image), preset_name="classic-black")
    assert report["timecode"]["mode"] == "none"
    assert report["timecode"]["text"] is None


def test_collision_numbering(sample_image):
    r1 = apply(str(sample_image), preset_name="classic-black")
    r2 = apply(str(sample_image), preset_name="classic-black")
    assert Path(r1["output"]).name == "sample_rec.png"
    assert Path(r2["output"]).name == "sample_rec_01.png"


def test_dry_run_writes_nothing(sample_image):
    report = apply(str(sample_image), dry_run=True, at_text="2026-11-03T14:30")
    assert report["dry_run"] is True
    assert not Path(report["output"]).exists()


def test_timecode_override_none(sample_image):
    report = apply(str(sample_image), timecode="none")
    assert report["timecode"]["mode"] == "none"


def test_output_same_as_input_rejected(sample_image):
    with pytest.raises(AgentError) as e:
        apply(str(sample_image), output=str(sample_image))
    assert e.value.exit_code == 2


def test_output_exists_needs_overwrite(sample_image, tmp_path):
    dest = tmp_path / "fixed.png"
    Image.new("RGB", (10, 10)).save(dest)
    with pytest.raises(AgentError) as e:
        apply(str(sample_image), output=str(dest))
    assert e.value.exit_code == 4
    report = apply(str(sample_image), output=str(dest), overwrite=True)
    assert Path(report["output"]) == dest


def test_missing_and_unsupported_input(tmp_path):
    with pytest.raises(AgentError) as e:
        apply(str(tmp_path / "nope.png"))
    assert e.value.exit_code == 3
    bad = tmp_path / "note.txt"
    bad.write_text("x", encoding="utf-8")
    with pytest.raises(AgentError) as e:
        apply(str(bad))
    assert e.value.exit_code == 3


def test_batch_shares_one_timestamp(tmp_path):
    src = tmp_path / "in"
    out = tmp_path / "out"
    src.mkdir()
    for name in ("a.png", "b.png"):
        Image.new("RGB", (320, 240), (30, 30, 30)).save(src / name)
    report, code = batch(str(src), str(out), at_text="2026-11-03T09:15")
    assert code == 0
    assert report["success"] == 2 and report["failed"] == 0
    assert report["timecode"]["text"] == "2026/11/03 AM 09:15"
    assert len(report["outputs"]) == 2
