import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from src.schemas.metadata import Metadata

router = APIRouter()
CUSTOM_META_DIR = Path(__file__).parent.parent.parent / "public" / "meta" / "custom"
DEFAULT_META_DIR = Path(__file__).parent.parent.parent / "public" / "meta" / "default"


def load_metadata_file_path(filename: str) -> Path:
    """メタデータファイルのパスを返す。customファイルが存在する場合はcustomファイルを読み、存在しない場合はdefaultファイルを読む"""
    custom_metadata_path = CUSTOM_META_DIR / filename
    metadata_path = custom_metadata_path if custom_metadata_path.exists() else DEFAULT_META_DIR / filename
    return metadata_path


@router.get("/meta")
async def get_metadata() -> Metadata:
    """
    レポート作成者情報などのメタデータを返す。
    custom/meta/metadata.jsonがあればそれを、なければdefault/meta/metadata.jsonを返す。
    デフォルト環境の場合は、画像やリンクの値は返さない。
    """
    try:
        metadata_path = load_metadata_file_path("metadata.json")
        with open(metadata_path) as f:
            metadata = json.load(f)

        # カスタムのメタデータかどうかを判定
        is_default = "default" in str(metadata_path)

        # デフォルト環境の場合は、画像やリンクの値は返さない
        if is_default:
            return Metadata(
                reporter=metadata.get("reporter"),
                message=metadata.get("message"),
                brandColor=metadata.get("brandColor"),
                isDefault=True,
            )

        # カスタム環境の場合は、すべての値を返す
        return Metadata(
            reporter=metadata.get("reporter"),
            message=metadata.get("message"),
            webLink=metadata.get("webLink"),
            privacyLink=metadata.get("privacyLink"),
            termsLink=metadata.get("termsLink"),
            brandColor=metadata.get("brandColor"),
            isDefault=False,
        )
    except FileNotFoundError:
        # メタデータファイルが存在しない場合は空のメタデータを返す
        return Metadata()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/meta/reporter.png")
async def get_reporter_image():
    """
    レポート作成者の画像を返す。
    custom/meta/report.pngが存在する場合のみ画像を返し、
    存在しない場合やdefaultのみの場合は204 No Contentを返す。
    → デフォルト画像（テスト環境など）が誤って表示されないようにするための仕様。
    """
    custom_metadata_path = CUSTOM_META_DIR / "reporter.png"
    if custom_metadata_path.exists():
        return FileResponse(custom_metadata_path)
    return Response(status_code=204)


@router.get("/meta/icon.png")
async def get_icon():
    return FileResponse(load_metadata_file_path("icon.png"))


@router.get("/meta/ogp.png")
async def get_ogp():
    return FileResponse(load_metadata_file_path("ogp.png"))


@router.get("/meta/metadata.json")
async def get_metadata_json() -> Metadata:
    """
    レポート作成者情報などのメタデータを返す。
    custom/meta/metadata.jsonがあればそれを、なければdefault/meta/metadata.jsonを返す。
    デフォルト環境の場合は、画像やリンクの値は返さない。
    """
    try:
        metadata_path = load_metadata_file_path("metadata.json")
        with open(metadata_path) as f:
            metadata = json.load(f)

        # カスタムのメタデータかどうかを判定
        is_default = "default" in str(metadata_path)

        # デフォルト環境の場合は、画像やリンクの値は返さない
        if is_default:
            return Metadata(
                reporter=metadata.get("reporter"),
                message=metadata.get("message"),
                brandColor=metadata.get("brandColor"),
                isDefault=True,
            )

        # カスタム環境の場合は、すべての値を返す
        return Metadata(
            reporter=metadata.get("reporter"),
            message=metadata.get("message"),
            webLink=metadata.get("webLink"),
            privacyLink=metadata.get("privacyLink"),
            termsLink=metadata.get("termsLink"),
            brandColor=metadata.get("brandColor"),
            isDefault=False,
        )
    except FileNotFoundError:
        # メタデータファイルが存在しない場合は空のメタデータを返す
        return Metadata()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
