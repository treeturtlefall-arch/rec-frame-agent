# UPSTREAM — 本家エンジンの出典とピン留め

- 出典: [treeturtlefall-arch/rec-frame-app](https://github.com/treeturtlefall-arch/rec-frame-app)（MIT、`LICENSE` を本リポジトリにも同梱）
- 同梱範囲: `src/rec_frame_agent/engine/` 以下の `rec_overlay.py` / `rec_config.py` / `rec_i18n.py` / `rec_batch.py` と `fonts/` / `assets/dots/`。GUI（`rec_frame_app.py`）は含めない（DESIGN.md §9 の方式 C）。
- 同梱スナップショット: 2026-11-02 の亜衣用ローカルフォーク由来（本家 v0.3.0 期）。フォーク側に正確なコミット SHA の記録がなかったため、版数の固定は**各ファイルの SHA-256** で行う。正本は `src/rec_frame_agent/data/engine_hashes.json` で、`doctor` の `engine_integrity` が照合する。
- 同梱ファイルは改変しない。変更が必要になった場合は、本家へ還す改善として切り出す。
- 同期手順: `scripts/sync_upstream.py <本家チェックアウトのパス>` が差分とハッシュを表示して止まる。取り込む場合はエンジンファイルと素材を差し替え、ハッシュマニフェストを再生成し、ゴールデンテストを通してから確定する。自動上書きはしない。
- 移行条件: 本家が import 可能なパッケージになったら、pip 依存へ移行して同梱を削除する（DESIGN.md §9）。
