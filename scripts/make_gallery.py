#!/usr/bin/env python3
"""軸別ギャラリーの見本をエンジン実物で生成する（DESIGN.md §17.3）。

土台は同梱のお気に入り（presets/ai-photo-white.json）。各見本は土台から
1軸だけを変えたもので、キャプション用の機械名を manifest.json に残す。
アーティファクト側は再現描画をせず、この生成物を表示するだけにする。

使い方: python scripts/make_gallery.py [出力フォルダ]（既定: gallery_output/）
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PIL import Image, ImageDraw  # noqa: E402

from rec_frame_agent.engine import load as load_engine  # noqa: E402

rec_config, rec_overlay, rec_batch = load_engine()

W, H = 640, 400
FIXED_DT = datetime(2026, 11, 3, 14, 30)
FIXED_TEXT = rec_overlay.format_photo_timecode(FIXED_DT)


def make_base_image(kind: str, path: Path) -> None:
    """明るい絵／暗い絵の2種のサンプルを描く（写真の代わりの判定用素材）。"""
    img = Image.new("RGB", (W, H))
    px = img.load()
    if kind == "bright":
        top, bottom = (168, 205, 232), (240, 228, 196)
    else:
        top, bottom = (16, 22, 38), (52, 44, 58)
    for y in range(H):
        t = y / H
        for x in range(W):
            px[x, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    d = ImageDraw.Draw(img)
    if kind == "bright":
        d.ellipse([470, 40, 570, 140], fill=(250, 214, 90))  # 太陽
        d.ellipse([80, 90, 300, 150], fill=(255, 255, 255))  # 雲
        d.polygon([(0, 400), (220, 210), (440, 400)], fill=(106, 148, 104))  # 山
        d.polygon([(240, 400), (460, 240), (640, 400)], fill=(84, 124, 92))
    else:
        d.ellipse([500, 36, 566, 102], fill=(226, 230, 238))  # 月
        for sx, sy in [(60, 50), (150, 90), (300, 40), (420, 80), (90, 150), (560, 170)]:
            d.ellipse([sx, sy, sx + 5, sy + 5], fill=(240, 240, 250))  # 星
        d.rectangle([0, 320, W, H], fill=(24, 26, 34))  # 地面
        d.rectangle([90, 220, 210, 320], fill=(38, 40, 52))  # 家
        d.rectangle([126, 258, 160, 292], fill=(250, 196, 92))  # 窓明かり
    img.save(path)
    # photo モードの解決を再現可能にするため mtime を固定する
    ts = datetime(2026, 10, 18, 10, 24).timestamp()
    os.utime(path, (ts, ts))


def variations(base_raw: dict) -> list[dict]:
    """(section, label, machine, overrides, timecode_mode) の一覧を作る。"""
    out: list[dict] = []

    def add(section, label, machine, overrides=None, mode=None):
        out.append({
            "section": section, "label": label, "machine": machine,
            "overrides": overrides or {}, "timecode_mode": mode,
        })

    for name in rec_config.COLOR_PRESETS:
        if name in ("black", "white"):
            add("color", f"色: {name}", f"--color {name}", {"color": name, "custom_color": ""})
        else:
            add("color", f"色: {name}", f"--color {name}", {"custom_color": name})
    for key, label in [("show_frame", "枠"), ("show_battery", "電池"), ("show_rec", "REC"),
                       ("show_red_dot", "赤丸")]:
        add("toggles", f"{label} OFF", f"{key}=false", {key: False})
    add("toggles", "中央十字 ON", "show_cross=true", {"show_cross": True})
    add("toggles", "タイムスタンプ OFF", "--timecode none", {}, mode="none")
    for font in rec_config.BUNDLED_FONT_CHOICES:
        add("font", f"フォント: {font}", f"--font '{font}'", {"font_key": font})
    for t in ("small", "medium", "large"):
        add("thickness", f"太さ: {t}", f"--thickness {t}", {"thickness": t})
    for e in ("off", "oled", "2000s"):
        add("effect", f"エフェクト: {e}", f"--effect {e}", {"effect": e})
    for r in (0, 2, 4, 6):
        add("retro", f"レトロ劣化: {r}", f"--retro {r}", {"retro_effect": r})
    for b in range(5):
        add("battery", f"電池バー: {b} 本", f"--battery {b}", {"battery_bars": b})
    for dot in rec_config.get_all_dot_styles():
        add("dot", f"ドット: {dot}", f"--dot {dot}", {"dot_style": dot})
    add("timecode", "処理した時刻", "--timecode processed_at", {}, mode="processed_at")
    add("timecode", "撮影日時", "--timecode photo", {}, mode="photo")
    add("timecode", "なし", "--timecode none", {}, mode="none")
    return out


def build_cfg(base_raw: dict, var: dict):
    from rec_frame_agent.agentfonts import inject as inject_agent_font

    merged = {k: v for k, v in base_raw.items() if k != "timecode_mode"}
    merged.update(var["overrides"])
    cfg = rec_config.OverlayConfig.from_dict(inject_agent_font(merged))
    mode = var["timecode_mode"] or base_raw.get("timecode_mode", "processed_at")
    if mode == "processed_at":
        cfg = replace(cfg, show_timecode=True, timecode_from_exif=False, timecode_text=FIXED_TEXT)
    elif mode == "photo":
        cfg = replace(cfg, show_timecode=True, timecode_from_exif=True)
    elif mode == "none":
        cfg = replace(cfg, show_timecode=False, timecode_from_exif=False)
    return cfg


def slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text).strip("_")[:60]


SECTION_LABELS = {
    "color": "色", "toggles": "要素の ON/OFF", "font": "フォント（同梱）",
    "thickness": "枠の太さ", "effect": "エフェクト", "retro": "レトロ劣化",
    "battery": "電池バー", "dot": "ドット素材", "timecode": "タイムスタンプ",
}

_PAGE_HEAD = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>rec-frame-agent 見本ギャラリー</title>
<style>
body{margin:0;font-family:system-ui,sans-serif;background:#14171c;color:#e8eaee}
header{padding:20px 20px 8px} h1{font-size:20px;margin:0 0 6px} p{color:#a7adb8;font-size:13px;line-height:1.6}
.switch{display:flex;gap:8px;margin:12px 20px}
.switch button{background:#232833;color:#e8eaee;border:1px solid #39404d;border-radius:999px;padding:6px 14px;cursor:pointer}
.switch button.active{background:#e8eaee;color:#14171c}
section{padding:8px 20px 4px} h2{font-size:15px;border-bottom:1px solid #2c333f;padding-bottom:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
figure{margin:0;background:#1b2027;border:1px solid #2c333f;border-radius:10px;overflow:hidden}
img{width:100%;display:block}
figcaption{padding:8px 10px;font-size:12px;display:flex;flex-direction:column;gap:4px}
code{color:#8fd0ff;font-size:11px;word-break:break-all}
.base-dark{display:none}
</style></head><body>
<header><h1>rec-frame-agent 見本ギャラリー</h1>
<p>土台はお気に入り（白枠／電池3本／REC／タイムスタンプは処理した時刻 __FIXED__）です。各見本は1つの軸だけを変えた実物描画です。気に入った見本の名前や下の機械名をチャットで伝えてください。そのまま設定として保存できます。</p></header>
<div class="switch"><button id="b-bright" class="active" onclick="show('bright')">明るい絵</button><button id="b-dark" onclick="show('dark')">暗い絵</button></div>
"""

_PAGE_TAIL = """
<script>
function show(k){document.querySelector('.base-bright').style.display=k=='bright'?'block':'none';document.querySelector('.base-dark').style.display=k=='dark'?'block':'none';document.getElementById('b-bright').classList.toggle('active',k=='bright');document.getElementById('b-dark').classList.toggle('active',k=='dark');}
</script></body></html>"""


def build_pages(out_dir: Path, manifest: dict) -> None:
    """index.html（相対参照版）と gallery.html（画像埋め込みの自己完結版）を出す。

    チャット等で単一ファイルとして開く場合は相対参照が解決されないため、
    納品は自己完結版を使う。
    """
    import base64

    def render(base: dict, embed: bool) -> str:
        by: dict[str, list] = {}
        for it in base["items"]:
            by.setdefault(it["section"], []).append(it)
        parts = []
        for sec, label in SECTION_LABELS.items():
            if sec not in by:
                continue
            cards = []
            for it in by[sec]:
                if embed:
                    uri = "data:image/jpeg;base64," + base64.b64encode(
                        (out_dir / it["file"]).read_bytes()
                    ).decode()
                else:
                    uri = it["file"]
                cards.append(
                    f'<figure><img loading="lazy" src="{uri}" alt="{it["label"]}">'
                    f'<figcaption>{it["label"]}<code>{it["machine"]}</code></figcaption></figure>'
                )
            parts.append(f'<section><h2>{label}</h2><div class="grid">{"".join(cards)}</div></section>')
        return "".join(parts)

    head = _PAGE_HEAD.replace("__FIXED__", manifest["fixed_timecode_text"])
    for filename, embed in (("index.html", False), ("gallery.html", True)):
        body = "".join(
            f'<div class="base-{b["kind"]}">{render(b, embed)}</div>'
            for b in manifest["bases"]
        )
        (out_dir / filename).write_text(head + body + _PAGE_TAIL, encoding="utf-8")


DECISION_SECTION_LABELS = {
    "font": "フォント（7種・実物）",
    "retro": "レトロ劣化",
    "frame": "枠フレーム",
    "timecode": "タイムスタンプ",
}


def decision_variations() -> list[dict]:
    """決定用に絞った軸だけ（DESIGN.md §17.3、2026-11-03 タツ決定）。"""
    out: list[dict] = []

    def add(section, label, machine, overrides=None, mode=None):
        out.append({"section": section, "label": label, "machine": machine,
                    "overrides": overrides or {}, "timecode_mode": mode})

    from rec_frame_agent.agentfonts import AGENT_FONTS

    fonts = [f for f in rec_config.BUNDLED_FONT_CHOICES if not f.startswith("DSEG7")]
    fonts += list(AGENT_FONTS)
    for font in fonts:
        add("font", f"フォント: {font}", f"--font '{font}'", {"font_key": font})
    for r in (0, 3, 6):
        add("retro", f"レトロ劣化: {r}", f"--retro {r}", {"retro_effect": r})
    add("frame", "枠フレーム: 有り", "show_frame=true", {})
    add("frame", "枠フレーム: 無し", "show_frame=false", {"show_frame": False})
    add("timecode", "タイムスタンプ: 有り", "--timecode processed_at", {}, mode="processed_at")
    add("timecode", "タイムスタンプ: 無し", "--timecode none", {}, mode="none")
    return out


def build_decision_page(out_dir: Path, items_by_base: dict[str, list[dict]]) -> None:
    """決定用ギャラリーの自己完結ページ（decision.html）を出す。"""
    import base64

    def render(base_kind: str, embed: bool) -> str:
        by: dict[str, list] = {}
        for it in items_by_base[base_kind]:
            by.setdefault(it["section"], []).append(it)
        parts = []
        for sec, label in DECISION_SECTION_LABELS.items():
            if sec not in by:
                continue
            cards = []
            for it in by[sec]:
                if embed:
                    uri = "data:image/jpeg;base64," + base64.b64encode(
                        (out_dir / it["file"]).read_bytes()
                    ).decode()
                else:
                    uri = it["file"]
                cards.append(
                    f'<figure><img loading="lazy" src="{uri}" alt="{it["label"]}">'
                    f'<figcaption>{it["label"]}<code>{it["machine"]}</code></figcaption></figure>'
                )
            parts.append(f'<section><h2>{label}</h2><div class="grid">{"".join(cards)}</div></section>')
        return "".join(parts)

    os_fonts = "".join(
        f'<li>{name} <code>--font \'{name}\'</code></li>' for name in rec_config.FONT_CHOICES
    )
    head = _PAGE_HEAD.replace("__FIXED__", FIXED_TEXT).replace(
        "rec-frame-agent 見本ギャラリー", "rec-frame-agent 決定用ギャラリー"
    )
    note = (
        '<section><h2>フォント集合についての注記</h2>'
        "<p>DSEG7 Classic（7セグLED）はグリフが69種のみで、' や ,、/ が無く文字が豆腐になるため、"
        "後継の DSEG14 Classic（14セグLED）と Audiowide の2種をエージェント同梱として加え、"
        "決定用は7種にしています（DSEG7 自体はエンジン同梱として引き続き指定はできます）。</p></section>"
        '<section><h2>OSフォント 10種（名前リスト）</h2>'
        "<p>以下は Windows 等、フォント実物のある環境でのみ正確に描けます。"
        "このページの生成環境（Linux）ではフォールバックになってしまうため、見本は付けていません。"
        "正確な見本は Windows で本スクリプトを再実行して生成します（将来対応）。"
        "名前で指定すること自体は今でもできます。</p>"
        f"<ul>{os_fonts}</ul></section>"
    )
    body = "".join(
        f'<div class="base-{kind}">{render(kind, True)}{note if kind == "bright" else ""}</div>'
        for kind in ("bright", "dark")
    )
    (out_dir / "decision.html").write_text(head + body + _PAGE_TAIL, encoding="utf-8")


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "gallery_output"
    base_raw = json.loads((REPO_ROOT / "presets" / "ai-photo-white.json").read_text(encoding="utf-8"))
    manifest = {"base_preset": "ai-photo-white", "fixed_timecode_text": FIXED_TEXT, "bases": []}
    for kind in ("bright", "dark"):
        src_dir = out_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        src = src_dir / f"base_{kind}.png"
        make_base_image(kind, src)
        items = []
        for i, var in enumerate(variations(base_raw)):
            cfg = build_cfg(base_raw, var)
            dest_dir = out_dir / kind / var["section"]
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{i:02d}_{slug(var['machine'])}.jpg"
            rec_batch.process_single_file(src, dest.with_suffix(".png"), cfg)
            # サムネイル用に JPEG 化して軽くする
            Image.open(dest.with_suffix(".png")).convert("RGB").save(dest, quality=82)
            dest.with_suffix(".png").unlink()
            items.append({
                "section": var["section"], "label": var["label"], "machine": var["machine"],
                "file": str(dest.relative_to(out_dir)),
            })
        manifest["bases"].append({"kind": kind, "items": items})
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    build_pages(out_dir, manifest)

    # 決定用ギャラリー（絞った軸のみ、自己完結ページ）
    decision_items: dict[str, list[dict]] = {}
    for kind in ("bright", "dark"):
        src = out_dir / "src" / f"base_{kind}.png"
        items = []
        for i, var in enumerate(decision_variations()):
            cfg = build_cfg(base_raw, var)
            dest_dir = out_dir / "decision" / kind / var["section"]
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{i:02d}_{slug(var['machine'])}.jpg"
            rec_batch.process_single_file(src, dest.with_suffix(".png"), cfg)
            Image.open(dest.with_suffix(".png")).convert("RGB").save(dest, quality=82)
            dest.with_suffix(".png").unlink()
            items.append({**var, "file": str(dest.relative_to(out_dir))})
        decision_items[kind] = items
    build_decision_page(out_dir, decision_items)

    total = sum(len(b["items"]) for b in manifest["bases"])
    d_total = sum(len(v) for v in decision_items.values())
    print(f"generated {total} catalog samples + {d_total} decision samples -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
