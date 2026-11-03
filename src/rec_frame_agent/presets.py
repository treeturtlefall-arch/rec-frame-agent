"""プリセットと「お気に入り」の名前解決（DESIGN.md §7）。

探索順:
  1. 実在するファイルパスなら直接使う
  2. ユーザープリセット ~/.config/rec-frame-agent/presets/<名前>.json
  3. リポジトリ同梱 presets/（チェックアウト実行時）
  4. パッケージ同梱 data/presets/
  別名（favorite / お気に入り等）は favorites.json で解決してから探す。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .errors import EXIT_USAGE, AgentError

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
REPO_PRESETS_DIR = PACKAGE_DIR.parents[1] / "presets"
REPO_FAVORITES = PACKAGE_DIR.parents[1] / "favorites.json"

TIMECODE_MODES = ("processed_at", "photo", "fixed", "none")
FAVORITE_WORDS = ("favorite", "お気に入り", "いつもの")


def user_config_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "rec-frame-agent"


def user_presets_dir() -> Path:
    return user_config_dir() / "presets"


def user_favorites_file() -> Path:
    return user_config_dir() / "favorites.json"


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise AgentError("invalid_json", EXIT_USAGE, f"JSON を読めません: {path}: {e}")
    if not isinstance(data, dict):
        raise AgentError("invalid_json", EXIT_USAGE, f"JSON の最上位はオブジェクトである必要があります: {path}")
    return data


def _bundled_preset_dirs() -> list[Path]:
    dirs = []
    for d in (REPO_PRESETS_DIR, DATA_DIR / "presets"):
        if d.is_dir() and d not in dirs:
            dirs.append(d)
    return dirs


def list_preset_files() -> list[tuple[str, Path]]:
    """(名前, ファイル) の一覧。ユーザープリセットが同梱より優先。"""
    found: dict[str, Path] = {}
    for d in _bundled_preset_dirs():
        for p in sorted(d.glob("*.json")):
            found.setdefault(p.stem, p)
    up = user_presets_dir()
    if up.is_dir():
        for p in sorted(up.glob("*.json")):
            found[p.stem] = p
    return sorted(found.items())


def preset_candidates() -> list[str]:
    return [name for name, _ in list_preset_files()]


def load_favorites() -> dict:
    """有効な favorites 定義。ユーザー側があればそれを正とし、無ければ同梱。"""
    for path in (user_favorites_file(), REPO_FAVORITES, DATA_DIR / "favorites.json"):
        if path.is_file():
            data = _read_json(path)
            return {
                "favorite": data.get("favorite"),
                "aliases": data.get("aliases") or {},
                "_file": str(path),
            }
    return {"favorite": None, "aliases": {}, "_file": None}


def resolve_target_name(requested: str) -> str:
    """favorite / 別名 を実プリセット名へ解決する。対象外はそのまま返す。"""
    fav = load_favorites()
    if requested in FAVORITE_WORDS and fav.get("favorite"):
        return str(fav["favorite"])
    aliases = fav.get("aliases") or {}
    if requested in aliases:
        return str(aliases[requested])
    if requested == "favorite":
        return requested
    return requested


@dataclass
class ResolvedPreset:
    requested: str
    resolved_name: str
    path: Path
    raw: dict

    @property
    def timecode_mode(self) -> str:
        mode = self.raw.get("timecode_mode")
        if mode in TIMECODE_MODES:
            return str(mode)
        if self.raw.get("timecode_from_exif"):
            return "photo"
        if self.raw.get("show_timecode"):
            return "fixed"
        return "none"

    def config_dict(self) -> dict:
        """本家 OverlayConfig へ渡す dict（拡張キー timecode_mode を除く）。"""
        return {k: v for k, v in self.raw.items() if k != "timecode_mode"}


def resolve_preset(requested: str) -> ResolvedPreset:
    # 1. 実在パス
    p = Path(requested).expanduser()
    if p.is_file():
        return ResolvedPreset(requested, p.stem, p, _read_json(p))
    # 2. 別名解決 → ファイル探索
    target = resolve_target_name(requested)
    up = user_presets_dir() / f"{target}.json"
    if up.is_file():
        return ResolvedPreset(requested, target, up, _read_json(up))
    for d in _bundled_preset_dirs():
        cand = d / f"{target}.json"
        if cand.is_file():
            return ResolvedPreset(requested, target, cand, _read_json(cand))
    raise AgentError(
        "preset_not_found",
        EXIT_USAGE,
        f"プリセットが見つかりません: {requested}",
        candidates=preset_candidates(),
    )


RESERVED_NAMES = set(FAVORITE_WORDS) | {"favorite"}


def set_user_favorite(name: str) -> Path:
    """ユーザー側 favorites.json にお気に入りを書く（既存の別名は保持）。"""
    fav = load_favorites()
    data = {"favorite": name, "aliases": fav.get("aliases") or {}}
    dest = user_favorites_file()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dest


def create_preset(
    name: str,
    fields: dict,
    *,
    timecode_mode: str | None = None,
    base_name: str | None = None,
    favorite: bool = False,
    overwrite: bool = False,
) -> dict:
    """ユーザープリセットを新規作成する（DESIGN.md §17.2）。

    fields は本家 OverlayConfig のキーで渡す。検証は本家に委ねる。
    """
    from .engine import load as load_engine
    from .errors import EXIT_OUTPUT_EXISTS

    if not name or "/" in name or "\\" in name or name.endswith(".json"):
        raise AgentError("invalid_preset_name", EXIT_USAGE, f"プリセット名が不正です: {name!r}")
    if name in RESERVED_NAMES:
        raise AgentError("invalid_preset_name", EXIT_USAGE, f"予約語はプリセット名に使えません: {name}")

    merged: dict = {}
    base_resolved = None
    if base_name:
        base_resolved = resolve_preset(base_name)
        merged = dict(base_resolved.config_dict())
        if timecode_mode is None:
            timecode_mode = base_resolved.timecode_mode
    merged.update(fields)
    if timecode_mode is not None:
        if timecode_mode not in TIMECODE_MODES:
            raise AgentError("invalid_timecode_mode", EXIT_USAGE, f"不明な timecode_mode: {timecode_mode}")
        merged["timecode_mode"] = timecode_mode
        merged["show_timecode"] = timecode_mode != "none"
        if timecode_mode == "photo":
            pass  # timecode_from_exif は fields / base 側に従う。下で立てる
            merged["timecode_from_exif"] = True
        elif timecode_mode in ("processed_at", "fixed"):
            merged["timecode_from_exif"] = False
    merged.setdefault("schema_version", 1)

    from .agentfonts import inject as inject_agent_font

    rec_config, _, _ = load_engine()
    try:
        validated = rec_config.OverlayConfig.from_dict(
            inject_agent_font({k: v for k, v in merged.items() if k != "timecode_mode"})
        )
    except (ValueError, TypeError) as e:
        raise AgentError("invalid_preset", EXIT_USAGE, f"設定が不正です: {e}")

    dest = user_presets_dir() / f"{name}.json"
    if dest.exists() and not overwrite:
        raise AgentError(
            "preset_exists", EXIT_OUTPUT_EXISTS,
            f"同名のユーザープリセットが既にあります: {dest}（--overwrite で上書き可）",
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fav_file = set_user_favorite(name) if favorite else None
    return {
        "ok": True,
        "name": name,
        "file": str(dest),
        "base": base_resolved.resolved_name if base_resolved else None,
        "timecode_mode": merged.get("timecode_mode", "none"),
        "config": validated.to_dict(),
        "favorite": favorite,
        "favorites_file": str(fav_file) if fav_file else None,
    }


def describe_preset(name: str, path: Path) -> dict:
    raw = _read_json(path)
    probe = ResolvedPreset(name, name, path, raw)
    return {
        "name": name,
        "file": str(path),
        "color": raw.get("color", "black"),
        "battery_bars": raw.get("battery_bars", 4),
        "show_rec": raw.get("show_rec", True),
        "timecode_mode": probe.timecode_mode,
    }
