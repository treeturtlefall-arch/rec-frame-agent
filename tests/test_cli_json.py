from __future__ import annotations

import json

from rec_frame_agent.cli import main


def _run(capsys, argv) -> tuple[int, dict]:
    code = main(argv)
    out = capsys.readouterr().out
    return code, json.loads(out)


def test_apply_json(sample_image, capsys):
    code, data = _run(capsys, ["apply", str(sample_image), "--json", "--at", "2026-11-03T14:30"])
    assert code == 0 and data["ok"] is True
    assert data["timecode"]["text"] == "2026/11/03 PM 02:30"


def test_preset_not_found_json(sample_image, capsys):
    code, data = _run(capsys, ["apply", str(sample_image), "--preset", "zzz", "--json"])
    assert code == 2 and data["ok"] is False
    assert data["error"]["code"] == "preset_not_found"


def test_presets_list_json(capsys):
    code, data = _run(capsys, ["presets", "--json", "list"])
    assert code == 0
    names = {p["name"] for p in data["presets"]}
    assert {"ai-photo-white", "classic-black"} <= names
    assert data["favorite"] == "ai-photo-white"


def test_doctor_json(capsys):
    code, data = _run(capsys, ["doctor", "--json"])
    assert code == 0 and data["ok"] is True
    assert all(c["ok"] for c in data["checks"])


def test_version_json(capsys):
    code, data = _run(capsys, ["version", "--json"])
    assert code == 0 and data["version"]


def test_set_favorite_roundtrip(capsys, sample_image):
    code, data = _run(capsys, ["presets", "--json", "set-favorite", "classic-black"])
    assert code == 0 and data["favorite"] == "classic-black"
    code, data = _run(capsys, ["apply", str(sample_image), "--json"])
    assert code == 0 and data["preset_resolved"] == "classic-black"
