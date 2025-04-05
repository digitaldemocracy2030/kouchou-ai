import json
import subprocess
import threading
from pathlib import Path
from typing import Any

import pandas as pd

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
        "is_pubcom": report_input.is_pubcom,
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
