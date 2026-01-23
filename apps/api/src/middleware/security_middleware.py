import re

from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse


def register_security_middleware(app: FastAPI):
    """
    不審なパターンのリクエストをブロックするミドルウェアを登録する関数。
    """

    @app.middleware("http")
    async def block_suspicious_requests(request: Request, call_next):
        # 環境変数ファイルへのアクセスなど、怪しいパスパターンを定義
        blocked_patterns = [r"/\.env.*", r"/config\.php", r"/wp-login\.php"]

        path = request.url.path
        for pattern in blocked_patterns:
            if re.match(pattern, path):
                return ORJSONResponse(status_code=403, content={"message": "Access forbidden"})

        response = await call_next(request)
        return response
