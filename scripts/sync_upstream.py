#!/usr/bin/env python3
"""本家チェックアウトと同梱エンジンの差分を表示する（上書きはしない）。

使い方: python scripts/sync_upstream.py <本家 rec-frame-app のパス>
取り込み手順は UPSTREAM.md を参照。
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ENGINE_FILES = ["rec_overlay.py", "rec_config.py", "rec_i18n.py", "rec_batch.py"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    upstream = Path(sys.argv[1]).expanduser()
    engine = Path(__file__).resolve().parents[1] / "src" / "rec_frame_agent" / "engine"
    if not upstream.is_dir():
        print(f"本家のパスが見つかりません: {upstream}")
        return 2
    changed = 0
    for name in ENGINE_FILES:
        src, dst = upstream / name, engine / name
        if not src.is_file():
            print(f"[missing] 本家に {name} がありません")
            changed += 1
            continue
        same = dst.is_file() and sha256(src) == sha256(dst)
        print(f"[{'same' if same else 'DIFF'}] {name}")
        changed += 0 if same else 1
    for sub in ("fonts", "assets/dots"):
        src_dir, dst_dir = upstream / sub, engine / sub
        s = {p.name for p in src_dir.glob("*")} if src_dir.is_dir() else set()
        d = {p.name for p in dst_dir.glob("*")} if dst_dir.is_dir() else set()
        print(f"[{'same' if s == d else 'DIFF'}] {sub}/ （本家 {len(s)} 件 / 同梱 {len(d)} 件）")
        changed += 0 if s == d else 1
    print("差分あり。取り込みは UPSTREAM.md の手順で手動で行ってください。" if changed else "同梱は本家と一致しています。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
