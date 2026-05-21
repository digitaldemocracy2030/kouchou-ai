import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Any

import polars as pl

from src.config import settings
from src.schemas.admin_report import ReportInput
from src.services.report_status import add_new_report_to_status, set_status, update_token_usage
from src.services.report_sync import ReportSyncService
from src.utils.logger import setup_logger

logger = setup_logger()
ANALYSIS_LOG_FILENAME = "analysis.log"
MAX_ERROR_LOG_CHARS = 4000


def _build_config(report_input: ReportInput) -> dict[str, Any]:
    comment_num = len(report_input.comments)

    config = {
        "name": report_input.input,
        "input": report_input.input,
        "question": report_input.question,
        "intro": report_input.intro,
        "model": report_input.model,
        "provider": report_input.provider,
        "is_pubcom": report_input.is_pubcom,
        "is_embedded_at_local": report_input.is_embedded_at_local,
        "local_llm_address": report_input.local_llm_address,
        "extraction": {
            "prompt": report_input.prompt.extraction,
            "workers": report_input.workers,
            "limit": comment_num,
        },
        "hierarchical_clustering": {
            "cluster_nums": report_input.cluster,
        },
        "hierarchical_initial_labelling": {
            "prompt": report_input.prompt.initial_labelling,
            "sampling_num": 30,
            "workers": report_input.workers,
        },
        "hierarchical_merge_labelling": {
            "prompt": report_input.prompt.merge_labelling,
            "sampling_num": 30,
            "workers": report_input.workers,
        },
        "hierarchical_overview": {"prompt": report_input.prompt.overview},
        "hierarchical_aggregation": {
            "sampling_num": report_input.workers,
        },
        "enable_source_link": report_input.enable_source_link,
    }

    return config


def _build_analysis_core_command(config_path: Path, only: str | None = None) -> list[str]:
    """Build the shared analysis-core CLI invocation used by the API.

    The Web product treats ``hierarchical_result.json`` as the canonical
    artifact and renders it through ``public-viewer``. We therefore keep
    ``--without-html`` enabled here so the CLI-only ``report.html`` sidecar
    is not generated, stored, or distributed by the API path.
    """
    cmd = [
        "python",
        "-m",
        "analysis_core",
        "--config",
        str(config_path),
        "--output-dir",
        str(settings.REPORT_DIR),
        "--input-dir",
        str(settings.INPUT_DIR),
        "--skip-interaction",
        "--without-html",
    ]
    if only:
        cmd.extend(["--only", only])
    return cmd


def save_config_file(report_input: ReportInput) -> Path:
    config = _build_config(report_input)
    config_path = settings.CONFIG_DIR / f"{report_input.input}.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    return config_path


def save_input_file(report_input: ReportInput) -> Path:
    """
    入力データをCSVファイルとして保存する

    Args:
        report_input: レポート生成の入力データ

    Returns:
        Path: 保存されたCSVファイルのパス
    """
    comments = []
    for comment in report_input.comments:
        # 基本フィールドの設定
        comment_data = {
            "comment-id": comment.id,
            "comment-body": comment.comment,
            "source": comment.source,
            "url": comment.url,
        }

        # 追加の属性フィールドを含める
        for key, value in comment.dict(exclude={"id", "comment", "source", "url"}).items():
            if value is not None:
                # すでに"attribute_"プレフィックスがついているかチェック
                comment_data[key] = value

        comments.append(comment_data)

    input_path = settings.INPUT_DIR / f"{report_input.input}.csv"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(comments)
    df.write_csv(input_path)
    return input_path


def _analysis_log_path(slug: str) -> Path:
    return settings.REPORT_DIR / slug / ANALYSIS_LOG_FILENAME


def _read_log_excerpt(log_path: Path, max_chars: int = MAX_ERROR_LOG_CHARS) -> str | None:
    if not log_path.exists():
        return None

    try:
        content = log_path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as exc:
        logger.warning(f"Failed to read analysis log for {log_path}: {exc}")
        return None

    if not content:
        return None

    if len(content) <= max_chars:
        return content

    return content[-max_chars:]


def _ensure_error_status_payload(slug: str, error_override: str | None = None) -> None:
    status_file = settings.REPORT_DIR / slug / "hierarchical_status.json"
    log_path = _analysis_log_path(slug)
    log_excerpt = _read_log_excerpt(log_path)

    status_data: dict[str, Any]
    if status_file.exists():
        try:
            with open(status_file, encoding="utf-8") as f:
                status_data = json.load(f)
        except Exception as exc:
            logger.warning(f"Failed to load status file for {slug}: {exc}")
            status_data = {}
    else:
        status_data = {}

    status_data["status"] = "error"
    status_data["current_job"] = status_data.get("current_job") or "error"
    status_data["error"] = (
        error_override
        or status_data.get("error")
        or "analysis-core exited with a non-zero status; see error_log_excerpt"
    )
    status_data["error_log_path"] = ANALYSIS_LOG_FILENAME
    status_data["error_log_excerpt"] = log_excerpt

    status_file.parent.mkdir(parents=True, exist_ok=True)
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2, ensure_ascii=False)


def _monitor_process(process: subprocess.Popen, slug: str, log_file: Any | None = None) -> None:
    """
    サブプロセスの実行を監視し、完了時にステータスを更新する

    Args:
        process: 監視対象のサブプロセス
        slug: レポートのスラッグ
        log_file: subprocess の stdout/stderr を書き込んでいるログファイルハンドル。完了時にクローズされる。
    """
    try:
        retcode = process.wait()
        if retcode == 0:
            # レポート生成成功時、ステータスを更新
            try:
                status_file = settings.REPORT_DIR / slug / "hierarchical_status.json"
                if status_file.exists():
                    with open(status_file, encoding="utf-8") as f:
                        status_data = json.load(f)
                        total_token_usage = status_data.get("total_token_usage", 0)
                        token_usage_input = status_data.get("token_usage_input", 0)
                        token_usage_output = status_data.get("token_usage_output", 0)

                        config_file = settings.CONFIG_DIR / f"{slug}.json"
                        provider = None
                        model = None
                        if config_file.exists():
                            with open(config_file, encoding="utf-8") as f:
                                config_data = json.load(f)
                                provider = config_data.get("provider")
                                model = config_data.get("model")

                        logger.info(
                            f"Found token usage in status file for {slug}: total={total_token_usage}, input={token_usage_input}, output={token_usage_output}, provider={provider}, model={model}"
                        )
                        update_token_usage(
                            slug,
                            total_token_usage,
                            token_usage_input,
                            token_usage_output,
                            provider,
                            model,
                        )
            except Exception as e:
                logger.error(f"Error updating token usage for {slug}: {e}")

            set_status(slug, "ready")

            logger.info(f"Syncing files for {slug} to storage")
            report_sync_service = ReportSyncService()
            # レポートファイルをストレージに同期し、JSONファイル以外を削除
            report_sync_service.sync_report_files_to_storage(slug)
            # 入力ファイルをストレージに同期し、ローカルファイルを削除
            report_sync_service.sync_input_file_to_storage(slug)
            # 設定ファイルをストレージに同期
            report_sync_service.sync_config_file_to_storage(slug)
            # ステータスファイルをストレージに同期
            report_sync_service.sync_status_file_to_storage()

        else:
            _ensure_error_status_payload(slug)
            set_status(slug, "error")
    finally:
        if log_file is not None:
            log_file.close()


def _launch_analysis_process(cmd: list[str], slug: str, env: dict[str, str]) -> subprocess.Popen:
    report_dir = settings.REPORT_DIR / slug
    report_dir.mkdir(parents=True, exist_ok=True)
    log_file = _analysis_log_path(slug).open("w", encoding="utf-8")
    try:
        process = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT)
    except Exception:
        log_file.close()
        raise
    threading.Thread(target=_monitor_process, args=(process, slug, log_file), daemon=True).start()
    return process


def _set_report_status_if_present(slug: str, status: str) -> None:
    try:
        set_status(slug, status)
    except ValueError:
        logger.info(f"Skip status update for {slug}: report status entry not found")


def launch_report_generation(report_input: ReportInput, user_api_key: str | None = None) -> None:
    """
    analysis-core パッケージを subprocess で呼び出してレポート生成処理を開始する関数。
    """
    try:
        add_new_report_to_status(report_input)
        config_path = save_config_file(report_input)
        save_input_file(report_input)
        cmd = _build_analysis_core_command(config_path)

        env = os.environ.copy()
        if user_api_key:
            env["USER_API_KEY"] = user_api_key

        _launch_analysis_process(cmd, report_input.input, env)
    except Exception as e:
        _ensure_error_status_payload(report_input.input, error_override=f"Failed to launch analysis-core: {e}")
        _set_report_status_if_present(report_input.input, "error")
        logger.error(f"Error launching report generation: {e}")
        raise e


def launch_report_generation_from_config(config_path: Path, slug: str, user_api_key: str | None = None) -> None:
    """
    既存のconfigファイルからanalysis-coreを起動する関数。
    """
    try:
        cmd = _build_analysis_core_command(config_path)

        env = os.environ.copy()
        if user_api_key:
            env["USER_API_KEY"] = user_api_key

        _launch_analysis_process(cmd, slug, env)
    except Exception as e:
        _ensure_error_status_payload(slug, error_override=f"Failed to launch analysis-core: {e}")
        _set_report_status_if_present(slug, "error")
        logger.error(f"Error launching report generation from config: {e}")
        raise e


def execute_aggregation(slug: str, user_api_key: str | None = None) -> bool:
    """
    analysis-core パッケージの集約処理のみ実行する関数
    """
    try:
        config_path = settings.CONFIG_DIR / f"{slug}.json"
        cmd = _build_analysis_core_command(config_path, only="hierarchical_aggregation")

        env = os.environ.copy()
        if user_api_key:
            env["USER_API_KEY"] = user_api_key

        _launch_analysis_process(cmd, slug, env)
        return True
    except Exception as e:
        _ensure_error_status_payload(slug, error_override=f"Failed to launch analysis-core: {e}")
        _set_report_status_if_present(slug, "error")
        logger.error(f"Error executing aggregation: {e}")
        return False
