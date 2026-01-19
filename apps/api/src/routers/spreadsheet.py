import os
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from src.config import settings
from src.services.spreadsheet_service import delete_input_file, process_spreadsheet_url
from src.utils.logger import setup_logger
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
    try:
        file_path = process_spreadsheet_url(input_data.url, input_data.file_name)
        return {
            "status": "success",
            "message": "スプレッドシートのインポートが完了しました",
            "file_path": str(file_path),
            "file_name": input_data.file_name,
        }
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
    input_path = settings.INPUT_DIR / f"{file_name}.csv"
    try:
        if not os.path.exists(input_path):
            raise HTTPException(status_code=404, detail=f"ファイル {file_name}.csv が見つかりません")

        df = pd.read_csv(input_path)

        # コメントデータをJSON形式に変換
        comments: list[dict[str, str | None]] = []
        for _, row in df.iterrows():
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
                if col not in ["comment-id", "comment", "source", "url"] and not pd.isna(row.get(col)):
                    # attribute_プレフィックスをつける
                    attribute_key = f"attribute_{col}" if not col.startswith("attribute_") else col
                    comment[attribute_key] = str(row.get(col))

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
        delete_input_file(file_name)
        return {
            "status": "success",
            "message": f"{file_name}.csvの削除が完了しました",
        }
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
