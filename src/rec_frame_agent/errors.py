"""終了コードと機械可読エラー（DESIGN.md §6.4）。"""
from __future__ import annotations

EXIT_OK = 0
EXIT_USAGE = 2  # 引数・設定エラー
EXIT_INPUT = 3  # 入力が無い／未対応形式
EXIT_OUTPUT_EXISTS = 4  # 出力が既に存在し --overwrite が無い
EXIT_ENGINE = 5  # エンジン内部の失敗


class AgentError(Exception):
    """--json でそのまま返せる形に整えるための例外。"""

    def __init__(self, code: str, exit_code: int, message: str, **extra):
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code
        self.message = message
        self.extra = extra

    def to_dict(self) -> dict:
        err = {"code": self.code, "message": self.message}
        err.update(self.extra)
        return {"ok": False, "error": err}
