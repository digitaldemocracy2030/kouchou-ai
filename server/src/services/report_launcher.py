import json
import subprocess
import threading
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.config import settings
from src.schemas.admin_report import ReportInput
from src.services.report_status import add_new_report_to_status, set_status
from src.services.report_sync import ReportSyncService
from src.utils.logger import setup_logger

logger = setup_logger()


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
    }
    return config


def save_config_file(report_input: ReportInput) -> Path:
    config = _build_config(report_input)
    config_path = settings.CONFIG_DIR / f"{report_input.input}.json"
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
    comments = [
        {
            "comment-id": comment.id,
            "comment-body": comment.comment,
            "source": comment.source,
            "url": comment.url,
        }
        for comment in report_input.comments
    ]
    input_path = settings.INPUT_DIR / f"{report_input.input}.csv"
    df = pd.DataFrame(comments)
    df.to_csv(input_path, index=False)
    return input_path


def _should_auto_generate_static_files(slug: str) -> bool:
    """
    入力データのサイズに基づいて、静的ファイルを自動生成すべきかを判断する

    Args:
        slug: レポートのスラッグ

    Returns:
        bool: 入力データが10,000以下の場合はTrue、それ以上の場合はFalse
    """
    try:
        input_file_path = settings.INPUT_DIR / f"{slug}.csv"
        if not input_file_path.exists():
            logger.warning(f"入力ファイルが存在しません: {input_file_path}")
            return False

        df = pd.read_csv(input_file_path)
        comment_count = len(df)

        logger.info(f"レポート {slug} の入力データ数: {comment_count}")

        return comment_count <= 10000
    except Exception as e:
        logger.error(f"入力データサイズの確認中にエラーが発生しました: {e}")
        return False


def _generate_static_files(slug: str) -> None:
    """
    特定のレポートの静的ファイルを生成する

    Args:
        slug: レポートのスラッグ
    """
    try:
        client_static_build_url = f"{settings.CLIENT_STATIC_BUILD_BASEPATH}/build/{slug}"
        response = requests.post(
            client_static_build_url,
            timeout=300,  # 大きなレポートの場合、生成に時間がかかる可能性があるため長めのタイムアウト
        )

        if response.status_code == 200:
            static_dir = settings.REPORT_DIR / slug / "static"
            static_dir.mkdir(exist_ok=True)

            with open(static_dir / "static.zip", "wb") as f:
                f.write(response.content)

            logger.info(f"レポート {slug} の静的ファイルを生成しました")

            # 静的ファイルをストレージに同期
            report_sync_service = ReportSyncService()
            report_sync_service.sync_static_files_to_storage(slug)
        else:
            logger.error(f"レポート {slug} の静的ファイル生成に失敗しました: {response.status_code}")
    except Exception as e:
        logger.error(f"レポート {slug} の静的ファイル生成中にエラーが発生しました: {e}")


def _monitor_process(process: subprocess.Popen, slug: str) -> None:
    """
    サブプロセスの実行を監視し、完了時にステータスを更新する

    Args:
        process: 監視対象のサブプロセス
        slug: レポートのスラッグ
    """
    retcode = process.wait()
    if retcode == 0:
        # レポート生成成功時、ステータスを更新
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

        if _should_auto_generate_static_files(slug):
            logger.info(f"レポート {slug} の静的ファイルを自動生成します")
            threading.Thread(target=_generate_static_files, args=(slug,), daemon=True).start()
        else:
            logger.info(f"レポート {slug} の入力データサイズが大きいため、静的ファイルは自動生成しません")
    else:
        set_status(slug, "error")


def launch_report_generation(report_input: ReportInput) -> None:
    """
    外部ツールの main.py を subprocess で呼び出してレポート生成処理を開始する関数。
    """
    try:
        add_new_report_to_status(report_input)
        config_path = save_config_file(report_input)
        save_input_file(report_input)
        cmd = ["python", "hierarchical_main.py", config_path, "--skip-interaction", "--without-html"]
        execution_dir = settings.TOOL_DIR / "pipeline"
        process = subprocess.Popen(cmd, cwd=execution_dir)
        threading.Thread(target=_monitor_process, args=(process, report_input.input), daemon=True).start()
    except Exception as e:
        set_status(report_input.input, "error")
        logger.error(f"Error launching report generation: {e}")
        raise e
