"""合成の実行層。描画は本家エンジンに委譲し、ここは名前解決・時刻注入・
命名・報告だけを行う（DESIGN.md §4、§6、§7.4）。"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from . import __version__
from .engine import load as load_engine
from .errors import (
    EXIT_ENGINE,
    EXIT_INPUT,
    EXIT_OK,
    EXIT_OUTPUT_EXISTS,
    EXIT_USAGE,
    AgentError,
)
from .presets import ResolvedPreset, resolve_preset

rec_config, rec_overlay, rec_batch = load_engine()

DATA_UPSTREAM = Path(__file__).resolve().parent / "data" / "upstream.json"


def _engine_info() -> dict:
    try:
        info = json.loads(DATA_UPSTREAM.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        info = {}
    return {
        "upstream": info.get("repo", "rec-frame-app"),
        "snapshot": info.get("snapshot", "unknown"),
        "agent_version": __version__,
    }


def _tz_label(dt: datetime) -> str:
    tz = dt.tzinfo
    if tz is None:
        return "local"
    return getattr(tz, "key", None) or dt.tzname() or str(tz)


def parse_at(value: str) -> datetime:
    """--at の ISO 形式（`2026-11-03T14:30` 等）を現地時刻として解釈する。"""
    text = value.strip().replace(" ", "T", 1)
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise AgentError(
            "invalid_at", EXIT_USAGE,
            f"--at の形式が不正です: {value}（例: 2026-11-03T14:30）",
        )
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return dt


def build_final_config(
    resolved: ResolvedPreset,
    *,
    timecode_override: str | None,
    at: datetime | None,
    started_at: datetime,
    input_path: Path | None = None,
) -> tuple[object, dict]:
    """プリセット → 本家 OverlayConfig と、報告用タイムコード情報。

    `processed_at` は本家に無い概念のため、ここで本家の書式に整形して
    `timecode_text` へ注入する（DESIGN.md §7.4）。エンジンは改変しない。
    """
    mode = timecode_override or resolved.timecode_mode
    if mode not in ("processed_at", "photo", "fixed", "none"):
        raise AgentError("invalid_timecode_mode", EXIT_USAGE, f"不明な timecode_mode: {mode}")
    if at is not None and timecode_override is None:
        mode = "processed_at"
    from .agentfonts import inject as inject_agent_font

    try:
        cfg = rec_config.OverlayConfig.from_dict(inject_agent_font(resolved.config_dict()))
    except (ValueError, TypeError) as e:
        raise AgentError("invalid_preset", EXIT_USAGE, f"プリセットの設定が不正です: {e}")

    if mode == "processed_at":
        dt = at or started_at
        text = rec_overlay.format_photo_timecode(dt)
        cfg = replace(cfg, show_timecode=True, timecode_from_exif=False, timecode_text=text)
        info = {
            "mode": mode,
            "text": text,
            "source": "fixed_by_--at" if at is not None else "agent_processed_at",
            "timezone": _tz_label(dt),
        }
    elif mode == "photo":
        cfg = replace(cfg, show_timecode=True, timecode_from_exif=True)
        text = None
        if input_path is not None:
            try:
                img = rec_overlay.load_base_image(input_path)
                text = rec_overlay.photo_timecode_text(img, input_path, cfg.timecode_text)
            except Exception:
                text = None
        info = {"mode": mode, "text": text, "source": "photo_exif_or_mtime", "timezone": _tz_label(started_at)}
    elif mode == "fixed":
        cfg = replace(cfg, show_timecode=True, timecode_from_exif=False)
        info = {"mode": mode, "text": cfg.timecode_text, "source": "preset_fixed", "timezone": _tz_label(started_at)}
    else:
        cfg = replace(cfg, show_timecode=False, timecode_from_exif=False)
        info = {"mode": mode, "text": None, "source": "none", "timezone": _tz_label(started_at)}
    return cfg, info


def _validate_input(input_path: Path) -> None:
    if not input_path.is_file():
        raise AgentError("input_not_found", EXIT_INPUT, f"入力画像が見つかりません: {input_path}")
    if input_path.suffix.lower() not in rec_config.SUPPORTED_EXTENSIONS:
        raise AgentError(
            "unsupported_format", EXIT_INPUT,
            f"未対応の形式です: {input_path.suffix}",
            supported=sorted(rec_config.SUPPORTED_EXTENSIONS),
        )


def _decide_output(input_path: Path, output: str | None, overwrite: bool) -> Path:
    if output:
        dest = Path(output).expanduser()
        if dest.resolve() == input_path.resolve():
            raise AgentError("output_same_as_input", EXIT_USAGE, "出力先に入力と同じパスは指定できません（元画像を守るため）")
        if dest.exists() and not overwrite:
            raise AgentError("output_exists", EXIT_OUTPUT_EXISTS, f"出力先が既に存在します: {dest}（--overwrite で上書き可）")
        return dest
    return rec_batch.resolve_output_path(input_path.parent, input_path)


def apply(
    input_file: str,
    *,
    preset_name: str = "favorite",
    output: str | None = None,
    timecode: str | None = None,
    at_text: str | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
    started_at: datetime | None = None,
) -> dict:
    started = started_at or datetime.now().astimezone()
    at = parse_at(at_text) if at_text else None
    input_path = Path(input_file).expanduser()
    _validate_input(input_path)
    resolved = resolve_preset(preset_name)
    cfg, tc_info = build_final_config(
        resolved, timecode_override=timecode, at=at, started_at=started, input_path=input_path
    )
    dest = _decide_output(input_path, output, overwrite)
    try:
        img = rec_overlay.load_base_image(input_path)
        width, height = img.size
    except Exception as e:
        raise AgentError("processing_failed", EXIT_ENGINE, f"画像を読めませんでした: {e}")
    report = {
        "ok": True,
        "input": str(input_path),
        "output": str(dest),
        "preset": preset_name,
        "preset_resolved": resolved.resolved_name,
        "preset_file": str(resolved.path),
        "width": width,
        "height": height,
        "timecode": tc_info,
        "engine": _engine_info(),
    }
    if dry_run:
        report["dry_run"] = True
        return report
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        rec_batch.process_single_file(input_path, dest, cfg)
    except Exception as e:
        raise AgentError("processing_failed", EXIT_ENGINE, f"合成に失敗しました: {e}")
    return report


def batch(
    input_dir: str,
    output_dir: str,
    *,
    preset_name: str = "favorite",
    timecode: str | None = None,
    at_text: str | None = None,
    timecode_per_file: bool = False,
    started_at: datetime | None = None,
) -> tuple[dict, int]:
    started = started_at or datetime.now().astimezone()
    at = parse_at(at_text) if at_text else None
    src_dir = Path(input_dir).expanduser()
    if not src_dir.is_dir():
        raise AgentError("input_not_found", EXIT_INPUT, f"入力フォルダが見つかりません: {src_dir}")
    resolved = resolve_preset(preset_name)
    cfg, tc_info = build_final_config(
        resolved, timecode_override=timecode, at=at, started_at=started
    )
    # バッチの processed_at は既定で全体同一時刻（build_final_config が
    # 固定文へ落とし込むため、そのまま process_folder で共有される）。
    # --timecode-per-file の時だけファイル毎に時刻を取り直して個別処理する。
    if timecode_per_file and tc_info["mode"] == "processed_at":
        dst_dir = Path(output_dir).expanduser()
        dst_dir.mkdir(parents=True, exist_ok=True)
        outputs, success, failed, skipped, errors = [], 0, 0, 0, []
        for src in sorted(p for p in src_dir.iterdir() if p.is_file()):
            if not rec_batch.is_supported_image(src):
                skipped += 1
                continue
            try:
                cfg_i, _ = build_final_config(
                    resolved, timecode_override=timecode, at=at,
                    started_at=datetime.now().astimezone(),
                )
                dest = rec_batch.resolve_output_path(dst_dir, src)
                rec_batch.process_single_file(src, dest, cfg_i)
                outputs.append(dest)
                success += 1
            except Exception as e:
                failed += 1
                errors.append(f"{src.name}: {e}")

        class _R:  # process_folder の結果と同じ形に揃える
            pass

        result = _R()
        result.success, result.failed, result.skipped = success, failed, skipped
        result.outputs, result.errors = outputs, errors
    else:
        result = rec_batch.process_folder(src_dir, Path(output_dir).expanduser(), cfg)
    report = {
        "ok": result.failed == 0,
        "input_dir": str(src_dir),
        "output_dir": str(output_dir),
        "preset": preset_name,
        "preset_resolved": resolved.resolved_name,
        "preset_file": str(resolved.path),
        "success": result.success,
        "failed": result.failed,
        "skipped": result.skipped,
        "outputs": [str(p) for p in result.outputs],
        "errors": list(result.errors),
        "timecode": tc_info,
        "timecode_per_file": timecode_per_file,
        "engine": _engine_info(),
    }
    return report, (EXIT_OK if result.failed == 0 else EXIT_ENGINE)
