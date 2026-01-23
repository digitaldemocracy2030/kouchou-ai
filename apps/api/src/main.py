from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from src.config import settings
from src.middleware.security_middleware import register_security_middleware
from src.routers import router
from src.services.report_status import load_status
from src.services.report_sync import initialize_from_storage
from src.utils.logger import setup_logger

slogger = setup_logger()


def get_app():
    print(settings.ENVIRONMENT)
    if settings.ENVIRONMENT == "production":
        return FastAPI(
            title="kouchou-ai API",
            default_response_class=ORJSONResponse,
            lifespan=lifespan,
            openapi_url=None,
            docs_url=None,
            redoc_url=None,
        )
    else:
        return FastAPI(
            title="kouchou-ai API",
            default_response_class=ORJSONResponse,
            lifespan=lifespan,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ストレージからファイルを初期化
    slogger.info(f"Initializing files from storage (type: {settings.STORAGE_TYPE})")
    success = initialize_from_storage()
    if success:
        slogger.info("Successfully initialized files from storage")
    else:
        slogger.warning("Failed to initialize some files from storage")

    # ステータスファイルをロード
    load_status()
    yield


app = get_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(
    router,
)

register_security_middleware(app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # エラーの詳細とスタックトレースをログに出力
    slogger.error(f"Request URL: {request.url} - Exception: {exc}", exc_info=True)
    return ORJSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )
