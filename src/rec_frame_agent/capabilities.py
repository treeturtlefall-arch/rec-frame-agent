"""能力カタログ（DESIGN.md §17.1）。

選択肢はエンジンの定数から動的に読む。ここに選択肢を写し書きしないことで、
エンジンが進化しても説明が古くならないようにする。
"""
from __future__ import annotations

from .agentfonts import list_agent_fonts
from .engine import load as load_engine
from .presets import load_favorites, resolve_preset

rec_config, rec_overlay, rec_batch = load_engine()

TOGGLES = [
    ("show_frame", "四隅の枠"),
    ("show_battery", "電池マーク"),
    ("show_rec", "REC 表示"),
    ("show_cross", "中央の十字"),
    ("show_timecode", "タイムスタンプ"),
    ("show_red_dot", "赤丸ドット"),
]

TIMECODE_MODES = {
    "processed_at": "処理した時刻を表示（エージェント向けの既定）",
    "photo": "撮影日時を表示（EXIF → ファイル更新時刻）",
    "fixed": "固定の文字列を表示",
    "none": "表示しない",
}


def build_capabilities() -> dict:
    fav = load_favorites()
    try:
        resolved = resolve_preset("favorite")
        current = {
            "favorite": fav.get("favorite"),
            "resolved": resolved.resolved_name,
            "config": resolved.config_dict(),
            "timecode_mode": resolved.timecode_mode,
        }
    except Exception as e:  # 解決できない環境でもカタログ自体は返す
        current = {"favorite": fav.get("favorite"), "error": str(e)}

    return {
        "ok": True,
        "summary": "画像にカメラのファインダー風フレーム（四隅枠・電池・REC・タイムスタンプ等）を合成する",
        "axes": {
            "color": {
                "label": "枠の色",
                "presets": list(rec_config.COLOR_PRESETS.keys()),
                "custom": "任意の HEX 色も指定可（custom_color）",
            },
            "font": {
                "label": "REC・日時のフォント",
                "bundled": list(rec_config.BUNDLED_FONT_CHOICES.keys()),
                "agent_bundled": list(list_agent_fonts().keys()),
                "os": list(rec_config.FONT_CHOICES.keys()),
                "note": "同梱フォントは環境に依存しない。OS フォントは環境により代替される場合がある。"
                        "DSEG7 Classic は ' , / 等のグリフが無く豆腐になるため、決定用には DSEG14 Classic（エージェント同梱）を推す",
            },
            "thickness": {
                "label": "枠の太さ",
                "choices": ["small", "medium", "large"],
                "range": "0–100 の数値でも指定可（四隅枠のみ連動）",
            },
            "toggles": {
                "label": "要素の ON/OFF",
                "items": [{"key": k, "label": label} for k, label in TOGGLES],
            },
            "battery_bars": {"label": "電池の残量バー", "range": [0, 1, 2, 3, 4]},
            "dot_style": {
                "label": "赤丸ドットの素材",
                "choices": rec_config.get_all_dot_styles(),
            },
            "effect": {
                "label": "質感エフェクト（オーバーレイ層のみ）",
                "choices": ["off", "oled", "2000s"],
                "retro_effect": {"label": "レトロ劣化の段階", "range": [0, 1, 2, 3, 4, 5, 6]},
            },
            "rec_label": {"label": "REC の文字列", "note": "自由な文字列に変更可"},
            "bg_box_opacity": {"label": "文字の座布団（半透明の下地）", "range": [0.0, 1.0]},
            "timecode_mode": {"label": "タイムスタンプの方式", "modes": TIMECODE_MODES},
        },
        "presets": {
            "note": "気に入った設定は名前付きプリセットとして保存でき、お気に入りにすると次から無指定で使える",
            "current": current,
        },
    }


def human_summary(caps: dict) -> str:
    axes = caps["axes"]
    lines = [
        caps["summary"] + "。",
        "",
        "変えられるもの:",
        f"- 色: {' / '.join(axes['color']['presets'])}（＋任意の HEX）",
        f"- フォント: エンジン同梱 {len(axes['font']['bundled'])} 種＋エージェント同梱 {len(axes['font']['agent_bundled'])} 種＋OS フォント {len(axes['font']['os'])} 種",
        "- ON/OFF: " + "、".join(t["label"] for t in axes["toggles"]["items"]),
        f"- 電池バー 0–4 本、ドット素材 {len(axes['dot_style']['choices'])} 種",
        "- エフェクト: off / oled / 2000s、レトロ劣化 0–6",
        "- タイムスタンプ: 処理した時刻 / 撮影日時 / 固定文 / なし",
        "",
        "気に入った組み合わせはプリセットとして保存でき、お気に入りにできます。",
    ]
    return "\n".join(lines)
