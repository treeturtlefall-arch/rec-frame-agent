# rec-frame-agent

AIエージェントから使うための REC フレーム合成。[rec-frame-app](https://github.com/treeturtlefall-arch/rec-frame-app)（本家、GUI製品）の描画エンジンをそのまま使い、本リポジトリはエージェントとエンジンの間の薄い翻訳層だけを担う。

> 「お気に入りのフレームをつけて」と Muse に言えば、フレームが付く。それがこのリポジトリの目的。

役割分担: 描画は本家、エージェント連携は本リポジトリ、動画は [rec-frame-ComfyUI](https://github.com/treeturtlefall-arch/rec-frame-ComfyUI)。設計の正本は [`DESIGN.md`](DESIGN.md)。

## インストール

```bash
git clone <このリポジトリ>
cd rec-frame-agent
uv tool install .        # または venv を作って pip install .
bash scripts/install_skill.sh   # Muse 用 SKILL.md の配置
rec-frame-agent doctor          # 全項目 OK で導入完了
```

要件: Python 3.11+ / Pillow（本家に合わせて 12.1.0 を固定）。GUI を含まないため tkinter は不要で、ヘッドレス環境でそのまま動く。

## 使い方

```bash
# お気に入りで1枚（プリセット無指定 = favorite）
rec-frame-agent apply photo.png --json

# プリセット指定・バリエーション
rec-frame-agent apply photo.png --preset classic-black
rec-frame-agent apply photo.png --timecode none          # タイムスタンプなし
rec-frame-agent apply photo.png --timecode photo         # 撮影日時（EXIF→mtime）
rec-frame-agent apply photo.png --at 2026-11-03T14:30    # 時刻を固定

# フォルダ一括（タイムスタンプは既定でバッチ全体で同一時刻）
rec-frame-agent batch input_dir output_dir --json

# プリセット管理と診断
rec-frame-agent presets list
rec-frame-agent presets set-favorite classic-black
rec-frame-agent doctor

# 能力カタログ（エージェントが「何ができる？」に答えるための動的取得）
rec-frame-agent capabilities --json

# プリセットを新規作成（土台＋差分、同時にお気に入り化も可）
rec-frame-agent presets create my-night --base favorite --color cyan --dot glow_red --favorite
```

見本ギャラリー（軸別に1項目だけ変えた実物見本、明るい絵／暗い絵）は `python scripts/make_gallery.py` で生成できます。気に入った見本の機械名をエージェントへ伝えれば、そのまま `presets create` の引数になります。

- 既定のお気に入りは **白枠／電池3本／REC／タイムスタンプは処理した時刻**（右下に `YYYY/MM/DD AM/PM HH:MM`）。中立な黒枠は `classic-black`。
- 元画像は上書きしない。出力は `{元名}_rec{拡張子}`、衝突時は `_rec_01` 連番。
- `--json` は成功・失敗とも機械可読で返し、終了コードは DESIGN.md §6.4 の表に従う。エージェントは JSON の `output` を正として報告する。

## Muse で使う

`skill/SKILL.md` が手順の正本。「お気に入りのフレームつけて」「RECフレームつけて」がトリガーになり、対象画像の特定 → 1コマンド実行 → 結果添付の報告までを規定している。

## ライセンス

MIT（本家エンジンの同梱については `UPSTREAM.md` と `LICENSE` を参照）。
