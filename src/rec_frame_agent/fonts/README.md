# エージェント同梱フォント

本家エンジンの同梱フォントは改変しない方針のため、rec-frame-agent 独自のフォントはここに置き、実行時にエンジンのカスタムフォント機構で登録する（DESIGN.md §17.4）。

| 表示名 | ファイル | 出典・ライセンス |
|---|---|---|
| `DSEG14 Classic(14セグLED)` | `DSEG14Classic-Bold.ttf` | keshikan DSEG v0.46 公式パッケージ。SIL OFL 1.1（`LICENSE-DSEG.txt`）。DSEG7 Classic の後継で、`'` `,` `/` 等を含む |
| `Audiowide(ワイドHUD)` | `Audiowide-Regular.ttf` | Google Fonts（Astigmatic）。SIL OFL 1.1（`OFL-Audiowide.txt`）。ASCII 完全収録 |

経緯: DSEG7 Classic は収録69グリフのみで、`'` `,` `/` 等が無く豆腐・欠落になる（7セグ表示の物理的制約として公式仕様）。決定用フォントの集合は、この2種を加え DSEG7 を外した7種とする（2026-11-03 タツ決定）。エンジン同梱の6種自体はカタログとしてはそのまま残る。
