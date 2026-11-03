"""エージェント同梱フォントの解決（DESIGN.md §17.4）。

プリセットには表示名だけを書き、絶対パスは持たせない。実行時にここが
実ファイルへのパスを引いて、本家 OverlayConfig の custom_fonts へ注入する。
これにより本家エンジン（vendored）には一切手を入れずにフォントを足せる。
"""
from __future__ import annotations

from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent / "fonts"

AGENT_FONTS: dict[str, str] = {
    "DSEG14 Classic(14セグLED)": "DSEG14Classic-Bold.ttf",
    "Audiowide(ワイドHUD)": "Audiowide-Regular.ttf",
}


def list_agent_fonts() -> dict[str, Path]:
    """{表示名: 実ファイル}。実在するものだけ返す。"""
    out: dict[str, Path] = {}
    for name, filename in AGENT_FONTS.items():
        p = FONTS_DIR / filename
        if p.is_file():
            out[name] = p
    return out


def is_agent_font(font_key: str | None) -> bool:
    return bool(font_key) and font_key in AGENT_FONTS


def inject(config_dict: dict) -> dict:
    """font_key がエージェントフォントなら custom_fonts へパスを注入した写しを返す。

    元の dict（＝プリセットファイルの内容）は変更しない。検証用・描画用の
    使い捨て dict に対して使うこと。
    """
    font_key = config_dict.get("font_key")
    fonts = list_agent_fonts()
    if font_key not in fonts:
        return config_dict
    merged = dict(config_dict)
    custom = dict(merged.get("custom_fonts") or {})
    custom[font_key] = str(fonts[font_key])
    merged["custom_fonts"] = custom
    return merged
