import os
from typing import Any

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.concurrency import run_in_threadpool
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from src.config import settings
from src.services.report_duplicate import ReportIdInUseError, guard_unused_report_id, slug_exists_anywhere
from src.services.spreadsheet_service import delete_input_file, process_spreadsheet_url
from src.utils.logger import setup_logger
from src.utils.slug_utils import validate_slug
from src.utils.validation import validate_filename

slogger = setup_logger()
router = APIRouter()

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


async def verify_admin_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    管理者APIキーを検証する関数

    Args:
        api_key: リクエストヘッダーから取得したAPIキー

    Returns:
        str: 検証されたAPIキー

    Raises:
        HTTPException: APIキーが無効な場合
    """
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


def ensure_not_existing_report(file_name: str) -> None:
    """既存レポートの入力 CSV（inputs/<slug>.csv）を取り込み・クリアで上書き・削除させない。

    作成前の取り込みで作られる inputs/<id>.csv だけの状態は、再取り込み・クリアを許すため衝突に含めない。
    ファイル名として不正な値は、ここでは判定せず呼び出し先の検証（400）に任せる。
    """
    valid, _ = validate_filename(file_name)
    if valid and slug_exists_anywhere(file_name, include_input=False):
        raise _report_id_in_use(ReportIdInUseError(file_name))


def _report_id_in_use(error: ReportIdInUseError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(error))


class SpreadsheetInput(BaseModel):
    url: str
    file_name: str


@router.post("/admin/spreadsheet/import")
async def import_spreadsheet(
    input_data: SpreadsheetInput, api_key: str = Depends(verify_admin_api_key)
) -> dict[str, str]:
    """
    スプレッドシートをインポートするエンドポイント

    Args:
        input_data: インポートするスプレッドシートの情報
        api_key: APIキー

    Returns:
        dict[str, str]: インポート結果

    Raises:
        HTTPException: インポート処理中にエラーが発生した場合
    """
    ensure_not_existing_report(input_data.file_name)
    try:
        # 外部 HTTP 取得を含む同期処理なので、イベントループを塞がないよう threadpool で実行する
        file_path = await run_in_threadpool(process_spreadsheet_url, input_data.url, input_data.file_name)
        return {
            "status": "success",
            "message": "スプレッドシートのインポートが完了しました",
            "file_path": str(file_path),
            "file_name": input_data.file_name,
        }
    except ReportIdInUseError as e:
        # 取得中に同じ ID でレポートが作られた
        raise _report_id_in_use(e) from e
    except ValueError as e:
        slogger.error(f"スプレッドシートのインポートエラー: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        slogger.error(f"予期せぬエラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部サーバーエラー: {str(e)}") from e


@router.get("/admin/spreadsheet/data/{file_name}")
async def get_spreadsheet_data(file_name: str, api_key: str = Depends(verify_admin_api_key)) -> dict[str, Any]:
    """
    インポート済みのスプレッドシートデータを取得するエンドポイント

    Args:
        file_name: 取得するファイル名
        api_key: APIキー

    Returns:
        dict[str, Any]: スプレッドシートのデータ

    Raises:
        HTTPException: データ取得中にエラーが発生した場合
    """
    # file_name はパス構成要素に使われるため、パストラバーサルを防ぐ
    validate_slug(file_name)
    input_path = settings.INPUT_DIR / f"{file_name}.csv"
    try:
        if not os.path.exists(input_path):
            raise HTTPException(status_code=404, detail=f"ファイル {file_name}.csv が見つかりません")

        # 型推論すると数値に見える comment-id が int になり、属性値の先頭の 0 も消えるため全列を文字列で読む
        df = pl.read_csv(input_path, infer_schema_length=0)

        # コメントデータをJSON形式に変換
        comments: list[dict[str, str | None]] = []
        for row in df.iter_rows(named=True):
            comment: dict[str, str | None] = {
                "id": row.get("comment-id", f"id-{len(comments) + 1}"),
                "comment": row.get("comment", ""),
            }

            # オプションフィールドを追加
            if "source" in df.columns:
                comment["source"] = row.get("source")
            if "url" in df.columns:
                comment["url"] = row.get("url")

            # その他のカラムを属性として追加
            for col in df.columns:
                col_value = row.get(col)
                if col not in ["comment-id", "comment", "source", "url"] and col_value is not None:
                    # attribute_プレフィックスをつける
                    attribute_key = f"attribute_{col}" if not col.startswith("attribute_") else col
                    comment[attribute_key] = str(col_value)

            comments.append(comment)

        return {"status": "success", "file_name": file_name, "comments": comments, "total": len(comments)}
    except HTTPException:
        raise
    except Exception as e:
        slogger.error(f"スプレッドシートデータの取得エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"データ取得中にエラーが発生しました: {str(e)}") from e


@router.delete("/admin/inputs/{file_name}")
async def delete_input(file_name: str, api_key: str = Depends(verify_admin_api_key)) -> dict[str, str]:
    # IDのバリデーション
    valid, message = validate_filename(file_name)
    if not valid:
        raise HTTPException(status_code=400, detail=message)

    try:
        # 既存レポートの判定から削除までをレポート作成と同じロックで囲み、
        # 判定のあとに作られたレポートの入力 CSV を消さない
        with guard_unused_report_id(file_name):
            delete_input_file(file_name)
        return {
            "status": "success",
            "message": f"{file_name}.csvの削除が完了しました",
        }
    except ReportIdInUseError as e:
        raise _report_id_in_use(e) from e
    except FileNotFoundError as e:
        slogger.warning(f"削除対象のファイルが見つかりません: {e}")
        # ファイルが見つからない場合も成功として扱う（冪等性のため）
        return {
            "status": "success",
            "message": f"{file_name}.csvは既に削除されているか存在しません",
        }
    except Exception as e:
        slogger.error(f"ファイル削除エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ファイル削除中にエラーが発生しました: {str(e)}") from e
