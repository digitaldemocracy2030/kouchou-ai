import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import polars as pl

from src.config import settings
from src.schemas.admin_report import ReportInput
from src.schemas.report import ReportStatus
from src.services.analysis_config import prune_config_for_mode, resolve_analysis_mode
from src.services.report_status import (
    add_new_report_to_status,
    load_status_as_reports,
    set_status_unless_deleted,
    update_token_usage,
)
from src.services.report_sync import ReportSyncService
from src.utils.logger import setup_logger

logger = setup_logger()
ANALYSIS_LOG_FILENAME = "analysis.log"
MAX_ERROR_LOG_CHARS = 4000


def _build_config(report_input: ReportInput) -> dict[str, Any]:
    comment_num = len(report_input.comments)

    # extraction / overview / aggregation は両モード共通のステップ。
    # 分析方式に依存するステップだけを analysis_mode で分岐する。
    config = {
        "name": report_input.input,
        "input": report_input.input,
        "question": report_input.question,
        "intro": report_input.intro,
        "model": report_input.model,
        "provider": report_input.provider,
        "analysis_mode": report_input.analysis_mode,
        "is_pubcom": report_input.is_pubcom,
        "is_embedded_at_local": report_input.is_embedded_at_local,
        "local_llm_address": report_input.local_llm_address,
        "extraction": {
            "prompt": report_input.prompt.extraction,
            "workers": report_input.workers,
            "limit": comment_num,
        },
        "hierarchical_overview": {"prompt": report_input.prompt.overview},
        # 埋め込みモデルはチャットモデルとは独立に選択できる。未指定なら embedding セクション
        # 自体を省略し、analysis-core の normalize_config 既定 (text-embedding-3-small) に委ねる。
        **({"embedding": {"model": report_input.embedding_model}} if report_input.embedding_model else {}),
        "hierarchical_aggregation": {
            "sampling_num": report_input.workers,
        },
        "enable_source_link": report_input.enable_source_link,
    }

    if report_input.analysis_mode == "llm_grouping":
        # LLM 直接グルーピングでは hierarchical_clustering と
        # 初期・統合ラベリングを行わず、llm_grouping ステップ
        # (group discovery + batch assignment) に置き換わる。
        # group discovery / assignment の prompt・パラメータは
        # analysis-core 側の既定値 (llm_grouping_specs.json) を使用するため、
        # ここでは明示セクションを付けない。
        # NOTE: analysis-core は analysis_mode ごとに許可される config キーを
        # 検証するため、hierarchical 専用セクションを含めてはいけない。
        pass
    else:
        config["hierarchical_clustering"] = {
            "cluster_nums": report_input.cluster,
        }
        disable_umap_model_saving(config)
        config["hierarchical_initial_labelling"] = {
            "prompt": report_input.prompt.initial_labelling,
            "sampling_num": 30,
            "workers": report_input.workers,
        }
        config["hierarchical_merge_labelling"] = {
            "prompt": report_input.prompt.merge_labelling,
            "sampling_num": 30,
            "workers": report_input.workers,
        }

    # 分岐で既に正しい section だけを組んでいるが、analysis_mode 非該当セクションが
    # 混入しないことを共通ヘルパで保証する（書き戻し経路と同じ不変条件）。
    return prune_config_for_mode(config)


def disable_umap_model_saving(config: dict[str, Any]) -> dict[str, Any]:
    """umap_model.pkl を保存させない（hierarchical モードの config のみ。in-place）。

    umap_model.pkl は #515 の UMAP 平面の使い回し（CLI 専用）のためのファイルで、
    Web 経路では読まれない。それでも件数に比例して大きくなり（6 万件で 1GB 超）、
    完了時にストレージへアップロードされるので、Web 経路では保存しない。

    save_umap_model を持たない config（この設定より前に作ったレポートの config ファイル、
    hierarchical_clustering が無い・null のもの）にも false を入れる。指定が無いと
    analysis-core の既定（保存する）になるため。明示した値（手で true にしたもの）は変えない。
    """
    if resolve_analysis_mode(config) != "hierarchical":
        return config
    clustering = config.get("hierarchical_clustering")
    if not isinstance(clustering, dict):
        clustering = config["hierarchical_clustering"] = {}
    clustering.setdefault("save_umap_model", False)
    return config


def _build_analysis_core_command(config_path: Path, only: str | None = None) -> list[str]:
    """Build the shared analysis-core CLI invocation used by the API.

    The Web product treats ``hierarchical_result.json`` as the canonical
    artifact and renders it through ``public-viewer``. We therefore keep
    ``--without-html`` enabled here so the CLI-only local ``report.html``
    artifact is not generated, stored, or distributed by the API path.
    """
    cmd = [
        # API を動かしているのと同一のインタプリタで analysis_core を起動する。
        # PATH 上の "python" を拾うと、venv / embeddable Python / python3 のみの
        # 環境では別の（analysis_core 未導入の）Python を呼んでしまう (#992)。
        sys.executable,
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
    with open(config_path, "w", encoding="utf-8") as f:
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
    schema = {"comment-id": pl.Utf8, "comment-body": pl.Utf8, "source": pl.Utf8, "url": pl.Utf8}
    for comment_data in comments:
        for key in comment_data:
            schema.setdefault(key, pl.Utf8)
    df = pl.DataFrame(comments, schema=schema)
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


UPLOAD_FAILED_ERROR = "Failed to upload report artifacts to storage"

# SIGKILL（9）で終了したとき。subprocess は -9、シェル経由やコンテナでは 128 + 9 = 137 になる。
# signal.SIGKILL は Windows に無いので数値で持つ。
_SIGKILL = 9
_SIGKILL_RETCODES = (-_SIGKILL, 128 + _SIGKILL)
SIGKILL_ERROR = (
    "analysis-core was killed by SIGKILL; this usually means it ran out of memory (OOM kill). "
    "Increase the memory available to the API container, or reduce the number of comments. "
    "See error_log_excerpt"
)


def _error_message_for_retcode(retcode: int) -> str | None:
    """終了コードから分かる失敗の理由を返す。分からなければ None（既定のエラー文を使う）。"""
    if retcode in _SIGKILL_RETCODES:
        return SIGKILL_ERROR
    return None


def _sync_report_artifacts_to_storage(slug: str) -> bool:
    """成果物・入力・設定ファイルをストレージに同期し、全て成功したかを返す"""
    logger.info(f"Syncing files for {slug} to storage")
    report_sync_service = ReportSyncService()
    try:
        # 1つが失敗しても残りは試み、結果を集約する
        results = [
            # レポートファイルをストレージに同期し、JSONファイル以外を削除
            report_sync_service.sync_report_files_to_storage(slug),
            # 入力ファイルをストレージに同期
            report_sync_service.sync_input_file_to_storage(slug),
            # 設定ファイルをストレージに同期
            report_sync_service.sync_config_file_to_storage(slug),
        ]
    except Exception as e:
        logger.error(f"Error syncing files for {slug} to storage: {e}")
        return False
    return all(results)


def _settle_completed_report(slug: str) -> None:
    """analysis-core が正常終了したレポートの成果物を同期し、成否に応じて status を確定する

    成果物のアップロードが一部でも失敗した状態で ready にすると、再起動後に結果ファイルの
    無い ready レポートが残るため、全て成功した場合だけ ready にする。
    実行中に削除されたレポートは deleted のまま保つ（set_status_unless_deleted）。
    """
    if _sync_report_artifacts_to_storage(slug):
        set_status_unless_deleted(slug, "ready")
    else:
        logger.error(f"Failed to sync report artifacts for {slug}; marking report as error")
        _ensure_error_status_payload(slug, error_override=UPLOAD_FAILED_ERROR)
        set_status_unless_deleted(slug, "error")


def _finalize_completed_report(slug: str) -> None:
    _settle_completed_report(slug)
    # ステータスファイルをストレージに同期
    ReportSyncService().sync_status_file_to_storage()


INTERRUPTED_ERROR = "Report generation was interrupted by an API server restart"


def _is_workflow_completed(slug: str) -> bool:
    report_dir = settings.REPORT_DIR / slug
    status_file = report_dir / "hierarchical_status.json"
    if not status_file.exists() or not (report_dir / "hierarchical_result.json").exists():
        return False
    try:
        with open(status_file, encoding="utf-8") as f:
            return json.load(f).get("status") == "completed"
    except Exception as exc:
        logger.warning(f"Failed to load status file for {slug}: {exc}")
        return False


def recover_interrupted_reports() -> None:
    """サーバー起動時に processing のまま残ったレポートの status を確定する

    analysis-core の終了を監視するスレッドはサーバープロセスと一緒に失われるため、
    再起動前に processing だったレポートはそのままだと processing に固着し、再実行も
    複製もできなくなる。成果物が完成していれば ready（同期失敗時は error）に、
    それ以外は error に遷移させる。

    制約: サーバープロセスだけが再起動し analysis-core のサブプロセスが生き残る場合
    （開発用の uvicorn --reload、ストレージを共有する複数インスタンスなど）も、実行中の
    レポートは error になる。その後ジョブが完了しても監視するものがないため error のまま残る。
    """
    try:
        interrupted = [r.slug for r in load_status_as_reports() if r.status == ReportStatus.PROCESSING]
    except Exception as e:
        logger.error(f"Failed to load report status for recovery: {e}")
        return
    if not interrupted:
        return

    for slug in interrupted:
        try:
            if _is_workflow_completed(slug):
                logger.info(f"Recovering interrupted report {slug}: workflow already completed")
                _settle_completed_report(slug)
            else:
                logger.warning(f"Recovering interrupted report {slug}: marking as error")
                _ensure_error_status_payload(slug, error_override=INTERRUPTED_ERROR)
                set_status_unless_deleted(slug, "error")
        except Exception as e:
            logger.error(f"Failed to recover interrupted report {slug}: {e}")

    ReportSyncService().sync_status_file_to_storage()


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

            _finalize_completed_report(slug)

        else:
            _ensure_error_status_payload(slug, _error_message_for_retcode(retcode))
            set_status_unless_deleted(slug, "error")
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
        set_status_unless_deleted(slug, status)
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
