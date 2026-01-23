import logging
import os
import sys
from typing import Literal

import structlog
from structlog.types import Processor

LogLevelType = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def setup_logger(
    log_level: LogLevelType | str | None = None,
    json_logs: bool = False,
    log_file: str | None = None,
    app_name: str = "app",
    third_party_loggers: list[str] | None = None,
) -> structlog.stdlib.BoundLogger:
    """
    Uvicornおよびアプリケーション全体で使用する一貫したロガーを設定する

    Args:
        log_level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: JSONフォーマットでログを出力するかどうか
        log_file: ログファイルのパス（指定しない場合は標準出力）
        app_name: アプリケーションロガーの名前
        third_party_loggers: 設定を適用する追加のサードパーティロガー名のリスト

    Returns:
        設定されたstructlogロガーインスタンス

    Examples:
        基本的な使用方法:
        ```python
        logger = setup_logger()
        logger.info("アプリケーション起動")
        ```

        JSONログとカスタムログレベル:
        ```python
        logger = setup_logger(log_level="DEBUG", json_logs=True)
        logger.debug("デバッグ情報", extra_data={"user_id": 123})
        ```

        ファイルへのログ出力:
        ```python
        logger = setup_logger(log_file="/var/log/myapp.log")
        logger.info("ファイルにログを記録")
        ```
    """
    # 定数の定義
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_THIRD_PARTY_LOGGERS = ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]

    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("azure.storage").setLevel(logging.WARNING)
    logging.getLogger("azure.identity").setLevel(logging.WARNING)

    try:
        # 環境変数またはデフォルト値からログレベルを取得
        if log_level is None:
            log_level = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

        # ログレベル文字列を数値に変換
        try:
            level = getattr(logging, log_level)
        except AttributeError:
            # 無効なログレベルの場合はデフォルトを使用
            print(f"Warning: Invalid log level '{log_level}'. Using {DEFAULT_LOG_LEVEL} instead.")
            level = getattr(logging, DEFAULT_LOG_LEVEL)

        # ハンドラーの設定
        handlers = _setup_handlers(log_file)

        # 標準のPythonロギングを設定
        logging.basicConfig(
            level=level,
            format="%(message)s",
            handlers=handlers,
            force=True,  # 既存の設定を上書き
        )

        # サードパーティのロガーを設定
        third_party_loggers = third_party_loggers or DEFAULT_THIRD_PARTY_LOGGERS
        _configure_third_party_loggers(third_party_loggers, level, handlers)

        # structlogのプロセッサーを設定
        processors = _get_structlog_processors(json_logs)

        # structlogを設定
        structlog.configure(
            processors=processors,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # ロガーを返す
        logger = structlog.get_logger(app_name)
        logger.info("Logger setup complete", log_level=log_level, json_logs=json_logs, log_file=log_file or "stdout")
        return logger
    except Exception as e:
        # セットアップ中に例外が発生した場合はフォールバックロガーを返す
        print(f"Error setting up logger: {e}")
        # 最小限の設定でロガーを作成
        structlog.configure(
            processors=[structlog.processors.JSONRenderer()],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
        )
        fallback_logger = structlog.get_logger("fallback")
        fallback_logger.error("Logger setup failed, using fallback configuration", error=str(e))
        return fallback_logger


def _setup_handlers(log_file: str | None = None) -> list[logging.Handler]:
    """ログハンドラーを設定する"""
    handlers = []

    try:
        if log_file:
            # ディレクトリが存在することを確認
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            handlers.append(file_handler)
        else:
            # 標準出力への出力を確保
            stream_handler = logging.StreamHandler(sys.stdout)
            handlers.append(stream_handler)
    except OSError as e:
        # ファイル操作エラーの場合は標準出力にフォールバック
        print(f"Error setting up log file: {e}. Falling back to stdout.")
        stream_handler = logging.StreamHandler(sys.stdout)
        handlers.append(stream_handler)

    return handlers


def _configure_third_party_loggers(logger_names: list[str], level: int, handlers: list[logging.Handler]) -> None:
    """サードパーティのロガーを設定する"""
    for logger_name in logger_names:
        module_logger = logging.getLogger(logger_name)
        module_logger.setLevel(level)
        module_logger.propagate = False

        # 既存のハンドラーをクリアしてから新しいハンドラーを追加
        module_logger.handlers = []
        for handler in handlers:
            module_logger.addHandler(handler)


def _get_structlog_processors(json_logs: bool = False) -> list[Processor]:
    """structlogのプロセッサーのリストを取得する"""
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # JSON形式の出力を設定
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True, exception_formatter=structlog.dev.plain_traceback))

    return processors
