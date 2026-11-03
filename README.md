# rec-frame-agent

> **「お気に入りのフレームをつけて」と Muse に言えば、フレームが付く。**

AIエージェントから使うための REC フレーム合成ツール。  
[rec-frame-app](https://github.com/treeturtlefall-arch/rec-frame-app)（本家・GUIアプリ）の描画エンジンをそのまま内蔵し、本リポジトリは **エージェントと描画エンジンの間の薄い翻訳層（CLI & スキル定義）** を担います。

<p align="center">
  <img src="assets/sample_before.webp" width="48%" alt="Before: 元画像" />
  <img src="assets/sample_after.webp" width="48%" alt="After: RECフレーム合成後" />
</p>
<p align="center">
  <em>左: 元画像 ／ 右: RECフレーム合成後（既定のお気に入り: ai-photo-white）</em>
</p>

---

## 📸 なにができるの？

- 🎬 **カメラファインダー風のREC演出を瞬時に合成**  
  四隅の枠、バッテリー残量アイコン、赤いRECインジケーター、タイムコードを画像に合わせて綺麗にレンダリングします。
- 🛡️ **文字の白飛び・黒飛びを自動防止（スマート座布団）**  
  白背景や明るい場所でも文字が埋もれないよう、枠色に連動した薄い半透明の背景ボックス（座布団）を自動で敷きます。
- 🕒 **柔軟なタイムスタンプ**  
  「処理した現在時刻」「写真の撮影日時（EXIF）」「指定日時」「タイムスタンプなし」を自在に切り替え可能。
- 📁 **フォルダ一括バッチ処理**  
  複数枚の画像も同一タイムスタンプまたは連番で一発合成。
- 🎨 **お好みの設定を名前付きで保存（プリセットとお気に入り）**  
  色、フォント（7セグLED、Audiowide等）、ドット形状（赤丸、glow等）を自分好みにカスタマイズし、`favorite`（お気に入り）として登録できます。

---

## 🤖 AIエージェント向け導入ガイド (For Muse.ai / AI Agents)

Muse.ai などの AI エージェントにこのリポジトリの URL が渡された場合、エージェントは以下の **3ステップ** で自律導入・検証してください。

### 1. インストールと依存解決
リポジトリ直下でツールとしてインストールします（GUI不要・tkinter不要・ヘッドレス環境完全対応）。
```bash
git clone <このリポジトリのURL>
cd rec-frame-agent
uv tool install .        # または pip install .
```

### 2. Muse スキルの配置
```bash
bash scripts/install_skill.sh
```
※ スキル定義ファイルが `~/workspace/custom-skills/rec-frame-agent/SKILL.md` に配置され、エージェントが「お気に入りのフレームをつけて」などの会話トリガーを認識できるようになります。

### 3. 診断（Doctor チェック）
```bash
rec-frame-agent doctor
```
出力の全項目が `[OK]` になっていればセットアップ完了です！

### エージェントの実行ルール（要約）
- **基本呼び出し**:
  ```bash
  rec-frame-agent apply <対象画像パス> --json
  ```
- **結果の報告**: `--json` の出力をパースし、`"ok": true` であれば `"output"` に格納されている画像パスを添付してユーザーに報告します。
- **詳細なトリガーや対応ルール**: [`skill/SKILL.md`](skill/SKILL.md) を正本として動作してください。

---

## 💻 人間用クイックスタート & CLI の使い方

### インストール
```bash
# uv をお使いの場合
uv tool install .

# 通常の pip / venv をお使いの場合
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install .
```

### よく使うコマンド
```bash
# 1. お気に入り設定で1枚合成（既定: ai-photo-white）
rec-frame-agent apply photo.png

# 2. プリセットを指定して合成
rec-frame-agent apply photo.png --preset classic-black

# 3. タイムスタンプのバリエーション
rec-frame-agent apply photo.png --timecode none          # タイムスタンプなし
rec-frame-agent apply photo.png --timecode photo         # 写真の撮影日時（EXIF→mtime）
rec-frame-agent apply photo.png --at 2026-11-03T14:30    # 指定日時に固定

# 4. 文字を見やすくする座布団の調整
rec-frame-agent apply photo.png --bg-opacity 0.25       # 濃いめ（白飛び防止を強化）
rec-frame-agent apply photo.png --bg-opacity 0.0        # 座布団なし

# 5. フォルダ内の画像を一括処理
rec-frame-agent batch input_dir output_dir --json
```

### プリセットとお気に入りの管理
```bash
# プリセット一覧とお気に入りの確認
rec-frame-agent presets list

# お気に入りの切り替え
rec-frame-agent presets set-favorite classic-black

# 新しいプリセットを作成してお気に入りに設定（現在のお気に入りをベースに差分指定）
rec-frame-agent presets create my-night --base favorite --color cyan --dot glow_red --favorite

# 利用可能なオプションや値の一覧（能力カタログ）を動的取得
rec-frame-agent capabilities --json
```

見本ギャラリー（軸別に1項目だけ変えた実物見本）は `python scripts/make_gallery.py` で生成できます。気に入った見本の機械名を指定すれば、そのまま `presets create` の引数になります。

### 仕様・安心設計
- **元画像は上書きしない**: 出力は `{元ファイル名}_rec.{拡張子}` に保存されます。同名ファイルが存在する場合は自動で `_rec_01` と連番になります。
- **機械可読な JSON 出力**: `--json` を付けることで、終了コードとともに出力パスや適用情報が完全な JSON 形式で返されます。

---

## 🏛️ 役割分担と設計

- **描画エンジン**: [rec-frame-app](https://github.com/treeturtlefall-arch/rec-frame-app)（本家・GUI製品）
- **エージェント連携層**: 本リポジトリ（CLI、JSON 出力、Muse 用スキル `SKILL.md`）
- **動画向け**: [rec-frame-ComfyUI](https://github.com/treeturtlefall-arch/rec-frame-ComfyUI)
- **設計正本**: システム仕様・終了コード一覧・テスト方針は [`DESIGN.md`](DESIGN.md) を参照。

---

## 📄 ライセンス

MIT License（本家エンジンの同梱ライセンスについては [`UPSTREAM.md`](UPSTREAM.md) および [`LICENSE`](LICENSE) を参照）。
