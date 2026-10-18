import json
import logging
import os
import threading
from datetime import UTC, datetime

import requests
from pydantic import ValidationError

from src.config import settings
from src.schemas.admin_report import ReportInput
from src.schemas.report import AnalysisData, Report, ReportStatus, ReportVisibility
from src.schemas.report_config import ReportConfigUpdate
from src.services.llm_pricing import LLMPricing
from src.services.report_sync import ReportSyncService

# ロガーの設定
logger = logging.getLogger("uvicorn")

STATE_FILE = settings.DATA_DIR / "report_status.json"
_lock = threading.RLock()
_report_status = {}


class StatusStorageSyncError(Exception):
    """report_status.json のストレージへの同期に失敗したことを表す例外"""


# FIXME: report_status.jsonのフォーマット変更に対応するためのコード。広聴AIをver3.0にした段階で削除する。
# https://github.com/digitaldemocracy2030/kouchou-ai/issues/507
def convert_old_format_status(status: dict) -> dict:
    """旧形式のレポートのステータスを新形式に変換する
    旧形式では公開/非公開をis_publicで管理していたが、新形式ではvisibilityで管理している

    v1.0.x のエントリ（と、v2.0.x で公開設定を一度も切り替えていないエントリ）は
    visibility も is_public も持たない。visibility は必須項目なので、補わないと一覧の
    読み込み全体が失敗する。公開範囲が記録されていないので、非公開として扱う。
    """
    for slug, report_status in status.items():
        if not isinstance(report_status, dict):
            continue
        if "slug" not in report_status:
            report_status["slug"] = slug

        if "is_public" in report_status:
            report_status["visibility"] = (
                ReportVisibility.PUBLIC.value if report_status["is_public"] else ReportVisibility.PRIVATE.value
            )
            report_status.pop("is_public")
            status[slug] = report_status
        elif "visibility" not in report_status:
            report_status["visibility"] = ReportVisibility.PRIVATE.value
    return status


def load_status() -> None:
    global _report_status
    # 読み込みとグローバル再代入を _lock で保護し、save_status() の書き込みと競合させない
    with _lock:
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                _report_status = convert_old_format_status(json.load(f))
        except FileNotFoundError:
            _report_status = {}
        except json.JSONDecodeError:
            _report_status = {}


def load_status_as_reports(include_deleted: bool = False) -> list[Report]:
    global _report_status
    # 読み込み・グローバル再代入・一覧構築まで _lock 内で行い、書き込み途中の状態を読まない
    with _lock:
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                _report_status = convert_old_format_status(json.load(f))
        except FileNotFoundError:
            _report_status = {}
        except json.JSONDecodeError:
            _report_status = {}

        # 1 件の不正なエントリで一覧全体（と公開ページ・起動時の復旧）を失敗させないよう、
        # 検証に通らないエントリは警告して飛ばす。保存時に消えないよう、生データは書き換えない。
        reports = []
        for key, report in _report_status.items():
            try:
                reports.append(Report(**report))
            except (ValidationError, TypeError) as e:
                logger.warning(f"Skipping invalid report status entry {key!r}: {e}")

        if not include_deleted:
            reports = [report for report in reports if report.status != ReportStatus.DELETED]

        return reports


def save_status() -> None:
    with _lock:
        # ディレクトリが存在しない場合は作成
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 同じディレクトリの一時ファイルに書き込んでから os.replace で atomic に差し替える。
        # open(STATE_FILE, "w") で直接書くと先に truncate されるため、書き込み途中に
        # 読み手(例: GET /admin/reports)が空ファイルを読むおそれがある。
        tmp_path = STATE_FILE.with_name(f"{STATE_FILE.name}.tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(_report_status, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, STATE_FILE)
        except Exception:
            # 書き込みに失敗したら一時ファイルを掃除して既存ファイルは温存する
            if tmp_path.exists():
                tmp_path.unlink()
            raise


def sync_status_to_storage() -> None:
    """report_status.json をストレージ（Azure Blob 等）へ同期する

    ローカルが一時的なファイルシステムの運用では、起動時にストレージ上の
    report_status.json が正として復元される。公開範囲の変更や削除をここで
    同期しないと、再起動で元の状態（公開・未削除）に戻ってしまう。
    _lock 内で呼ぶことで、並行する更新より古い内容が後から上書きアップロードされないようにする。

    Raises:
        StatusStorageSyncError: アップロードに失敗した場合
    """
    with _lock:
        try:
            synced = ReportSyncService().sync_status_file_to_storage()
        except Exception as e:
            raise StatusStorageSyncError(f"Failed to sync report status to storage: {e}") from e
        if not synced:
            raise StatusStorageSyncError("Failed to sync report status to storage")


def add_new_report_to_status(report_input: ReportInput) -> None:
    with _lock:
        _report_status[report_input.input] = {
            "slug": report_input.input,
            "source_slug": None,
            "status": "processing",
            "title": report_input.question,
            "description": report_input.intro,
            "is_pubcom": report_input.is_pubcom,
            "visibility": ReportVisibility.UNLISTED.value,
            "created_at": datetime.now(UTC).isoformat(),  # タイムゾーン付きISO形式で追加
            "token_usage": 0,  # トークン使用量を初期化
            "token_usage_input": 0,  # 入力トークン使用量を初期化
            "token_usage_output": 0,  # 出力トークン使用量を初期化
            "estimated_cost": None,  # 推定コストを初期化
            "provider": None,  # LLMプロバイダーを初期化
            "model": None,  # LLMモデルを初期化
        }
        save_status()


def add_new_report_to_status_from_config(slug: str, config: dict, source_slug: str | None = None) -> None:
    with _lock:
        _report_status[slug] = {
            "slug": slug,
            "source_slug": source_slug,
            "status": "processing",
            "title": config.get("question", ""),
            "description": config.get("intro", ""),
            "is_pubcom": config.get("is_pubcom", False),
            "visibility": ReportVisibility.UNLISTED.value,
            "created_at": datetime.now(UTC).isoformat(),
            "token_usage": 0,
            "token_usage_input": 0,
            "token_usage_output": 0,
            "estimated_cost": None,
            "provider": config.get("provider"),
            "model": config.get("model"),
        }
        save_status()


def slug_exists(slug: str) -> bool:
    load_status()
    return slug in _report_status


def delete_report_from_status(slug: str) -> None:
    with _lock:
        if slug in _report_status:
            del _report_status[slug]
            save_status()


def set_status(slug: str, status: str) -> None:
    with _lock:
        if slug not in _report_status:
            raise ValueError(f"slug {slug} not found in report status")
        _report_status[slug]["status"] = status
        save_status()


def set_status_unless_deleted(slug: str, status: str) -> bool:
    """削除済み (deleted) でなければ status を書き換え、書き換えたかを返す

    analysis-core の終了を監視する側（生成・再集計の完了時）が使う。実行中に管理画面から
    削除されたレポートを完了時に ready / error へ上書きすると、削除前の公開状態のまま
    一覧に復活するため、確認と書き換えを同じロック内で行い、deleted は保つ。
    """
    with _lock:
        if slug not in _report_status:
            raise ValueError(f"slug {slug} not found in report status")
        if _report_status[slug].get("status") == ReportStatus.DELETED.value:
            logger.info(f"Skip status update to {status} for {slug}: report is deleted")
            return False
        _report_status[slug]["status"] = status
        save_status()
        return True


def get_status(slug: str) -> str:
    with _lock:
        return _report_status.get(slug, {}).get("status", "undefined")


def add_report_warning(slug: str, code: str) -> None:
    """レポートの status に警告コードを追記する（同じコードは重ねない）

    レポートは作成できたが、結果が利用者の想定と違いうること（例: 複製元の入力を作り直した）を残す。
    """
    with _lock:
        if slug not in _report_status:
            logger.warning(f"slug {slug} not found in report status when adding warning {code}")
            return
        warnings = _report_status[slug].setdefault("warnings", [])
        if code not in warnings:
            warnings.append(code)
        save_status()


def invalidate_report_cache(slug: str) -> None:
    # Next.jsのキャッシュを破棄するAPIを呼び出す
    try:
        logger.info(f"Attempting to revalidate Next.js cache for report: {slug}")

        # 環境変数からrevalidate URLを取得
        revalidate_url = settings.REVALIDATE_URL

        logger.info(f"Using revalidate API at: {revalidate_url}")

        response = requests.post(
            revalidate_url,
            json={"tag": f"report-{slug}", "secret": settings.REVALIDATE_SECRET},
            timeout=3,  # タイムアウトを短く設定
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            logger.info(f"Successfully revalidated Next.js cache for tag: report-{slug}")
        else:
            logger.error(f"Failed to revalidate: {response.status_code} {response.text}")
    except Exception as e:
        # revalidateに失敗しても、メタデータの更新は成功しているので例外は投げない
        logger.error(f"Failed to call revalidate API for {slug}: {e}")


def update_report_visibility_state(slug: str, new_visibility: ReportVisibility) -> str:
    with _lock:
        if slug not in _report_status:
            raise ValueError(f"slug {slug} not found in report status")
        # enumの値を文字列に変換して保存
        _report_status[slug]["visibility"] = new_visibility.value

        save_status()
        visibility = _report_status[slug]["visibility"]
        try:
            sync_status_to_storage()
        finally:
            # 同期に失敗してもローカルの変更は有効なので、キャッシュは破棄する
            invalidate_report_cache(slug)
    return visibility


def update_token_usage(
    slug: str,
    token_usage: int,
    token_usage_input: int | None = None,
    token_usage_output: int | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> None:
    """レポートのトークン使用量と推定コストを更新する

    Args:
        slug: レポートのスラッグ
        token_usage: トークン使用量（合計）
        token_usage_input: 入力トークン使用量（オプション）
        token_usage_output: 出力トークン使用量（オプション）
        provider: LLMプロバイダー名（オプション）
        model: モデル名（オプション）

    Raises:
        ValueError: 指定されたスラッグのレポートが存在しない場合
    """
    with _lock:
        if slug not in _report_status:
            logger.warning(f"slug {slug} not found in report status when updating token usage")
            return

        _report_status[slug]["token_usage"] = token_usage

        if token_usage_input is not None:
            _report_status[slug]["token_usage_input"] = token_usage_input

        if token_usage_output is not None:
            _report_status[slug]["token_usage_output"] = token_usage_output

        if provider is not None:
            _report_status[slug]["provider"] = provider
            logger.info(f"Updated provider for {slug}: {provider}")

        if model is not None:
            _report_status[slug]["model"] = model
            logger.info(f"Updated model for {slug}: {model}")

        if (
            token_usage_input is not None
            and token_usage_output is not None
            and provider is not None
            and model is not None
        ):
            estimated_cost = LLMPricing.calculate_cost(provider, model, token_usage_input, token_usage_output)
            _report_status[slug]["estimated_cost"] = estimated_cost
            logger.info(f"Updated estimated cost for {slug}: {LLMPricing.format_cost(estimated_cost)}")

        logger.info(
            f"Updated token usage for {slug} in report status: total={token_usage}, input={token_usage_input}, output={token_usage_output}"
        )
        save_status()


def update_report_config(slug: str, updated_config: ReportConfigUpdate) -> dict:
    """レポートのメタデータ（タイトル、説明）を更新する

    Args:
        slug: レポートのスラッグ
        title: 新しいタイトル（Noneの場合は更新しない）
        description: 新しい説明（Noneの場合は更新しない）

    Returns:
        更新後のレポート情報

    Raises:
        ValueError: 指定されたスラッグのレポートが存在しない場合
    """
    with _lock:
        if slug not in _report_status:
            raise ValueError(f"slug {slug} not found in report status")

        # タイトルの更新（指定された場合のみ）
        if updated_config.question is not None:
            _report_status[slug]["title"] = updated_config.question

        # 説明の更新（指定された場合のみ）
        if updated_config.intro is not None:
            _report_status[slug]["description"] = updated_config.intro

        save_status()
        updated_report = _report_status[slug]
        try:
            sync_status_to_storage()
        finally:
            invalidate_report_cache(slug)
    return updated_report


def add_analysis_data(report: Report) -> Report:
    if report.status != ReportStatus.READY:
        return report

    report_path = settings.REPORT_DIR / report.slug / "hierarchical_result.json"
    try:
        with open(report_path, encoding="utf-8") as f:
            report_result = json.load(f)

        analysis_data = AnalysisData(
            comment_num=report_result.get("comment_num", 0),
            arguments_num=len(report_result.get("arguments", [])),
            cluster_num=get_cluster_num(report_result),
        )

        return report.model_copy(update={"analysis": analysis_data})

    except FileNotFoundError:
        logger.warning(f"[add_analysis_data] File not found: {report_path}")
    except json.JSONDecodeError as e:
        logger.error(f"[add_analysis_data] JSON decode error for {report_path}: {e}")
    except Exception as e:
        logger.exception(f"[add_analysis_data] Unexpected error for {report_path}: {e}")

    return report


def get_cluster_num(result: dict) -> int:
    return sum(1 for c in result.get("clusters", []) if c.get("level") == 1)
