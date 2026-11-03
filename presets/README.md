# 同梱プリセット

| 名前 | 見た目 | タイムスタンプ |
|---|---|---|
| `ai-photo-white` | 白枠／電池3本／REC／十字なし／レトロ劣化なし。既定のお気に入り | 処理した時刻（`processed_at`）を右下に表示 |
| `classic-black` | 黒枠／電池4本／REC／十字なし。本家の簡易モード相当 | なし |

形式は本家 `OverlayConfig` の部分 JSON で、足りない項目は本家の既定値で吸収される。拡張キー `timecode_mode`（`processed_at` / `photo` / `fixed` / `none`）はこのリポジトリの翻訳層が解釈する（DESIGN.md §7.4）。

自分のプリセットは `~/.config/rec-frame-agent/presets/<名前>.json` に置くと、同梱より優先して使われる。お気に入りの差し替えは `rec-frame-agent presets set-favorite <名前>`。
