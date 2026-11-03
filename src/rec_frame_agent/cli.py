"""rec-frame-agent CLI（DESIGN.md §6）。

出力の契約:
- --json 指定時は成功・失敗とも標準出力へ JSON 1つだけを出す（§6.3）。
- 終了コードは §6.4 の表に従う。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import __version__
from .engine import ENGINE_DIR, engine_file_sha256, load as load_engine
from .errors import EXIT_ENGINE, EXIT_OK, EXIT_USAGE, AgentError
from .presets import (
    create_preset,
    describe_preset,
    list_preset_files,
    load_favorites,
    resolve_preset,
    set_user_favorite,
    user_config_dir,
    user_favorites_file,
)
from .runner import apply as run_apply
from .runner import batch as run_batch


def _emit(report: dict, as_json: bool, human: str | None = None) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif human is not None:
        print(human)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


def _fail(err: AgentError, as_json: bool) -> int:
    if as_json:
        print(json.dumps(err.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"エラー: {err.message}", file=sys.stderr)
        cands = err.extra.get("candidates")
        if cands:
            print(f"候補: {', '.join(cands)}", file=sys.stderr)
    return err.exit_code


def _wants_json(args) -> bool:
    return bool(getattr(args, "json", False))


def cmd_apply(args) -> int:
    as_json = _wants_json(args)
    try:
        report = run_apply(
            args.input,
            preset_name=args.preset,
            output=args.output,
            timecode=args.timecode,
            at_text=args.at,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
    except AgentError as e:
        return _fail(e, as_json)
    human = (
        f"{'（dry-run）' if report.get('dry_run') else ''}合成しました: {report['output']}\n"
        f"プリセット: {report['preset_resolved']} / タイムスタンプ: "
        f"{report['timecode']['mode']}"
        + (f"（{report['timecode']['text']}）" if report["timecode"].get("text") else "")
    )
    _emit(report, as_json, human)
    return EXIT_OK


def cmd_batch(args) -> int:
    as_json = _wants_json(args)
    try:
        report, code = run_batch(
            args.input_dir,
            args.output_dir,
            preset_name=args.preset,
            timecode=args.timecode,
            at_text=args.at,
            timecode_per_file=args.timecode_per_file,
        )
    except AgentError as e:
        return _fail(e, as_json)
    human = (
        f"一括処理: 成功 {report['success']} / 失敗 {report['failed']} / "
        f"スキップ {report['skipped']}（プリセット: {report['preset_resolved']}）"
    )
    _emit(report, as_json, human)
    return code


def cmd_presets(args) -> int:
    as_json = _wants_json(args)
    try:
        if args.presets_cmd == "list":
            items = [describe_preset(name, path) for name, path in list_preset_files()]
            fav = load_favorites()
            report = {"ok": True, "favorite": fav.get("favorite"), "presets": items}
            human = "\n".join(
                f"- {i['name']}（{i['color']} / 電池{i['battery_bars']}本 / timecode: {i['timecode_mode']}）"
                for i in items
            ) + f"\nお気に入り: {fav.get('favorite')}"
            _emit(report, as_json, human)
            return EXIT_OK
        if args.presets_cmd == "show":
            resolved = resolve_preset(args.name)
            from .runner import build_final_config
            from datetime import datetime

            cfg, tc = build_final_config(
                resolved, timecode_override=None, at=None,
                started_at=datetime.now().astimezone(),
            )
            report = {
                "ok": True,
                "requested": args.name,
                "preset_resolved": resolved.resolved_name,
                "preset_file": str(resolved.path),
                "timecode_mode": resolved.timecode_mode,
                "config": cfg.to_dict(),
                "timecode_preview": tc,
            }
            _emit(report, as_json)
            return EXIT_OK
        if args.presets_cmd == "set-favorite":
            # 実プリセットとして存在することだけ確認する（favorite 経由では探さない）
            target = args.name
            found = any(name == target for name, _ in list_preset_files())
            if not found:
                raise AgentError(
                    "preset_not_found", EXIT_USAGE,
                    f"プリセットが見つかりません: {target}",
                    candidates=[n for n, _ in list_preset_files()],
                )
            dest = set_user_favorite(target)
            report = {"ok": True, "favorite": target, "file": str(dest)}
            _emit(report, as_json, f"お気に入りを {target} にしました（{dest}）")
            return EXIT_OK
        if args.presets_cmd == "create":
            fields = _create_fields(args)
            report = create_preset(
                args.name,
                fields,
                timecode_mode=args.timecode,
                base_name=args.base,
                favorite=args.favorite,
                overwrite=args.overwrite,
            )
            human = f"プリセットを作成しました: {report['name']}（{report['file']}）"
            if report["favorite"]:
                human += " / お気に入りに設定"
            _emit(report, as_json, human)
            return EXIT_OK
    except AgentError as e:
        return _fail(e, as_json)
    return EXIT_USAGE


def _onoff(value: str | None) -> bool | None:
    if value is None:
        return None
    return value == "on"


def _create_fields(args) -> dict:
    """presets create の CLI 引数を OverlayConfig のフィールドへ翻訳する。"""
    from .engine import load as load_engine

    rec_config, _, _ = load_engine()
    fields: dict = {}
    if args.color is not None:
        c = args.color.strip()
        if c.lower() in ("black", "white"):
            fields["color"] = c.lower()
            fields["custom_color"] = ""
        elif c.lower() in rec_config.COLOR_PRESETS or c.startswith("#"):
            fields["custom_color"] = c
        else:
            raise AgentError(
                "invalid_color", EXIT_USAGE,
                f"色が不正です: {args.color}（プリセット名か #HEX で指定）",
                candidates=list(rec_config.COLOR_PRESETS.keys()),
            )
    if args.font is not None:
        fields["font_key"] = args.font
    if args.thickness is not None:
        t = args.thickness
        fields["thickness"] = int(t) if t.isdigit() else t
    if args.battery is not None:
        fields["battery_bars"] = args.battery
    if args.dot is not None:
        fields["dot_style"] = args.dot
    if args.effect is not None:
        fields["effect"] = args.effect
    if args.retro is not None:
        fields["retro_effect"] = args.retro
    if args.rec_label is not None:
        fields["rec_label"] = args.rec_label
    if args.timecode_text is not None:
        fields["timecode_text"] = args.timecode_text
    if args.bg_opacity is not None:
        fields["bg_box_opacity"] = args.bg_opacity
    for attr, key in (("frame", "show_frame"), ("battery_toggle", "show_battery"),
                      ("rec", "show_rec"), ("cross", "show_cross"), ("red_dot", "show_red_dot")):
        v = _onoff(getattr(args, attr))
        if v is not None:
            fields[key] = v
    return fields


def cmd_capabilities(args) -> int:
    from .capabilities import build_capabilities, human_summary

    caps = build_capabilities()
    _emit(caps, _wants_json(args), human_summary(caps))
    return EXIT_OK


def _engine_hashes() -> dict[str, str]:
    manifest_path = Path(__file__).resolve().parent / "data" / "engine_hashes.json"
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def cmd_doctor(args) -> int:
    as_json = _wants_json(args)
    checks: list[dict] = []

    import platform

    py_ok = sys.version_info >= (3, 11)
    checks.append({"name": "python", "ok": py_ok, "detail": platform.python_version()})

    try:
        import PIL

        checks.append({"name": "pillow", "ok": True, "detail": PIL.__version__})
    except Exception as e:
        checks.append({"name": "pillow", "ok": False, "detail": str(e)})

    try:
        load_engine()
        checks.append({"name": "engine_import", "ok": True, "detail": str(ENGINE_DIR)})
    except Exception as e:
        checks.append({"name": "engine_import", "ok": False, "detail": str(e)})

    fonts = sorted((ENGINE_DIR / "fonts").glob("*.ttf"))
    checks.append({"name": "engine_fonts", "ok": len(fonts) >= 6, "detail": f"{len(fonts)} fonts"})

    hashes = _engine_hashes()
    mismatched = []
    for name, want in hashes.items():
        p = ENGINE_DIR / name
        got = engine_file_sha256(p)
        if got != want:
            mismatched.append(name)
    checks.append({
        "name": "engine_integrity",
        "ok": bool(hashes) and not mismatched,
        "detail": "改変なし" if not mismatched else f"不一致: {mismatched}",
    })

    try:
        resolved = resolve_preset("favorite")
        checks.append({"name": "favorite_resolvable", "ok": True,
                       "detail": f"favorite -> {resolved.resolved_name}（{resolved.path}）"})
    except AgentError as e:
        checks.append({"name": "favorite_resolvable", "ok": False, "detail": e.message})

    from datetime import datetime

    now = datetime.now().astimezone()
    checks.append({"name": "timezone", "ok": True,
                   "detail": f"{now.tzname()} / 現在 {now.strftime('%Y/%m/%d %H:%M')}"})

    try:
        d = user_config_dir()
        d.mkdir(parents=True, exist_ok=True)
        checks.append({"name": "user_config_writable", "ok": True, "detail": str(d)})
    except OSError as e:
        checks.append({"name": "user_config_writable", "ok": False, "detail": str(e)})

    ok = all(c["ok"] for c in checks)
    report = {"ok": ok, "version": __version__, "checks": checks}
    human = "\n".join(f"[{'OK' if c['ok'] else 'NG'}] {c['name']}: {c['detail']}" for c in checks)
    _emit(report, as_json, human)
    return EXIT_OK if ok else EXIT_ENGINE


def cmd_version(args) -> int:
    from .runner import _engine_info

    report = {"ok": True, "name": "rec-frame-agent", "version": __version__, "engine": _engine_info()}
    _emit(report, _wants_json(args), f"rec-frame-agent {__version__}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rec-frame-agent", description="AIエージェント向け REC フレーム合成")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_apply = sub.add_parser("apply", help="1枚合成")
    p_apply.add_argument("input")
    p_apply.add_argument("--preset", default="favorite")
    p_apply.add_argument("-o", "--output", default=None)
    p_apply.add_argument("--timecode", choices=("processed_at", "photo", "fixed", "none"), default=None)
    p_apply.add_argument("--at", default=None, help="processed_at の時刻を固定する（例: 2026-11-03T14:30）")
    p_apply.add_argument("--json", action="store_true")
    p_apply.add_argument("--dry-run", action="store_true")
    p_apply.add_argument("--overwrite", action="store_true")
    p_apply.set_defaults(func=cmd_apply)

    p_batch = sub.add_parser("batch", help="フォルダ一括処理")
    p_batch.add_argument("input_dir")
    p_batch.add_argument("output_dir")
    p_batch.add_argument("--preset", default="favorite")
    p_batch.add_argument("--timecode", choices=("processed_at", "photo", "fixed", "none"), default=None)
    p_batch.add_argument("--at", default=None)
    p_batch.add_argument("--timecode-per-file", action="store_true")
    p_batch.add_argument("--json", action="store_true")
    p_batch.set_defaults(func=cmd_batch)

    p_presets = sub.add_parser("presets", help="プリセット管理")
    p_presets.add_argument("--json", action="store_true")
    presets_sub = p_presets.add_subparsers(dest="presets_cmd", required=True)
    p_list = presets_sub.add_parser("list")
    p_show = presets_sub.add_parser("show")
    p_show.add_argument("name")
    p_set = presets_sub.add_parser("set-favorite")
    p_set.add_argument("name")
    p_create = presets_sub.add_parser("create", help="ユーザープリセットを新規作成")
    p_create.add_argument("name")
    p_create.add_argument("--base", default=None, help="土台にする既存プリセット名")
    p_create.add_argument("--color", default=None, help="色プリセット名（black/white/green/cyan/red/yellow）か #HEX")
    p_create.add_argument("--font", default=None, help="フォント名（capabilities 参照）")
    p_create.add_argument("--thickness", default=None, help="small|medium|large|0-100")
    p_create.add_argument("--battery", type=int, default=None, help="電池バー 0-4")
    p_create.add_argument("--dot", default=None, help="ドット素材名")
    p_create.add_argument("--effect", choices=("off", "oled", "2000s"), default=None)
    p_create.add_argument("--retro", type=int, default=None, help="レトロ劣化 0-6")
    p_create.add_argument("--rec-label", default=None)
    p_create.add_argument("--timecode", choices=("processed_at", "photo", "fixed", "none"), default=None)
    p_create.add_argument("--timecode-text", default=None, help="fixed の文字列")
    p_create.add_argument("--bg-opacity", type=float, default=None, help="座布団の不透明度 0.0-1.0")
    p_create.add_argument("--frame", choices=("on", "off"), default=None)
    p_create.add_argument("--battery-toggle", choices=("on", "off"), default=None)
    p_create.add_argument("--rec", choices=("on", "off"), default=None)
    p_create.add_argument("--cross", choices=("on", "off"), default=None)
    p_create.add_argument("--red-dot", choices=("on", "off"), default=None)
    p_create.add_argument("--favorite", action="store_true", help="作成と同時にお気に入りにする")
    p_create.add_argument("--overwrite", action="store_true")
    # サブコマンド側でも --json を受け付ける（SUPPRESS で親指定を上書きしない）
    for p in (p_list, p_show, p_set, p_create):
        p.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    p_presets.set_defaults(func=cmd_presets)

    p_caps = sub.add_parser("capabilities", help="能力カタログ（選択軸と選択肢）")
    p_caps.add_argument("--json", action="store_true")
    p_caps.set_defaults(func=cmd_capabilities)

    p_doctor = sub.add_parser("doctor", help="自己診断")
    p_doctor.add_argument("--json", action="store_true")
    p_doctor.set_defaults(func=cmd_doctor)

    p_version = sub.add_parser("version", help="版数表示")
    p_version.add_argument("--json", action="store_true")
    p_version.set_defaults(func=cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
