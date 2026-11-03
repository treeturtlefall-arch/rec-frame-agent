"""本家 rec-frame-app の描画エンジン（ピン留め同梱、改変なし）へのローダ。

同梱ファイルは本家同様にトップレベル import（`from rec_config import ...`）
前提のため、このフォルダを sys.path に入れてから import する。
同梱ファイル自体は一切改変しない（DESIGN.md §9、UPSTREAM.md 参照）。
"""
from __future__ import annotations

import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent


def ensure_path() -> Path:
    """エンジンのフォルダを sys.path へ（重複挿入はしない）。"""
    p = str(ENGINE_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)
    return ENGINE_DIR


def load():
    """(rec_config, rec_overlay, rec_batch) を返す。"""
    ensure_path()
    import rec_batch
    import rec_config
    import rec_overlay

    return rec_config, rec_overlay, rec_batch
