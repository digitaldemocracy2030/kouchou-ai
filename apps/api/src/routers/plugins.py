"""
Plugin discovery and management API endpoints.

These endpoints allow the admin UI to:
1. Discover available input plugins
2. Check plugin configuration status
3. Validate plugin settings
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.plugins.base import PluginConfigError
from src.plugins.registry import PluginRegistry, load_builtin_plugins
from src.routers.admin_report import verify_admin_api_key

logger = logging.getLogger("uvicorn")

router = APIRouter()

# Load plugins on module import
load_builtin_plugins()


class PluginManifestResponse(BaseModel):
    """Response model for plugin manifest."""

    id: str
    name: str
    description: str
    version: str
    icon: str | None
    enabledByDefault: bool
    isAvailable: bool
    missingSettings: list[str]
    settings: list[dict]


class PluginListResponse(BaseModel):
    """Response model for plugin list."""

    plugins: list[PluginManifestResponse]


class ValidateSourceRequest(BaseModel):
    """Request model for source validation."""

    pluginId: str
    source: str


class ValidateSourceResponse(BaseModel):
    """Response model for source validation."""

    isValid: bool
    error: str | None


@router.get("/admin/plugins", dependencies=[Depends(verify_admin_api_key)])
async def list_plugins() -> PluginListResponse:
    """
    List all registered input plugins.

    Returns all plugins with their availability status.
    Unavailable plugins will have isAvailable=false and
    missingSettings will list the required settings that are not configured.
    """
    manifests = PluginRegistry.get_all_manifests()
    return PluginListResponse(plugins=[PluginManifestResponse(**m) for m in manifests])


@router.get("/admin/plugins/{plugin_id}", dependencies=[Depends(verify_admin_api_key)])
async def get_plugin(plugin_id: str) -> PluginManifestResponse:
    """
    Get details for a specific plugin.

    Returns the plugin manifest with configuration status.
    """
    manifest = PluginRegistry.get_manifest(plugin_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")
    return PluginManifestResponse(**manifest.to_dict())


@router.post("/admin/plugins/{plugin_id}/validate-source", dependencies=[Depends(verify_admin_api_key)])
async def validate_source(plugin_id: str, request: ValidateSourceRequest) -> ValidateSourceResponse:
    """
    Validate a source URL/identifier for a plugin.

    This checks if the source is valid for the given plugin
    without actually fetching any data.
    """
    plugin = PluginRegistry.get_plugin(plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    # Check if plugin is configured
    if not plugin.manifest.is_available():
        _, errors = plugin.manifest.validate_settings()
        return ValidateSourceResponse(isValid=False, error=f"Plugin not configured: {'; '.join(errors)}")

    is_valid, error = plugin.validate_source(request.source)
    return ValidateSourceResponse(isValid=is_valid, error=error)


class ImportRequest(BaseModel):
    """Request model for data import."""

    source: str
    fileName: str
    maxResults: int | None = 1000
    includeReplies: bool | None = False


class ImportResponse(BaseModel):
    """Response model for data import."""

    success: bool
    filePath: str | None
    commentCount: int
    comments: list[dict]
    error: str | None


@router.post("/admin/plugins/{plugin_id}/import", dependencies=[Depends(verify_admin_api_key)])
async def import_data(plugin_id: str, request: ImportRequest) -> ImportResponse:
    """
    Import data from a plugin source.

    Fetches data from the source and saves it as a CSV file
    in the input directory.
    """
    plugin = PluginRegistry.get_plugin(plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    try:
        # Fetch data from source
        df = plugin.fetch_data(
            request.source,
            max_results=request.maxResults,
            include_replies=request.includeReplies,
        )

        # Save to CSV
        file_path = plugin.save_to_csv(df, request.fileName)

        logger.info(f"Imported {len(df)} comments from {plugin_id} to {file_path}")

        return ImportResponse(
            success=True,
            filePath=str(file_path),
            commentCount=len(df),
            comments=df.to_dict(orient="records"),
            error=None,
        )

    except PluginConfigError as e:
        logger.error(f"Plugin configuration error: {e}")
        return ImportResponse(
            success=False,
            filePath=None,
            commentCount=0,
            comments=[],
            error=str(e),
        )
    except ValueError as e:
        logger.error(f"Import error: {e}")
        return ImportResponse(
            success=False,
            filePath=None,
            commentCount=0,
            comments=[],
            error=str(e),
        )
    except Exception as e:
        logger.exception(f"Unexpected error during import: {e}")
        return ImportResponse(
            success=False,
            filePath=None,
            commentCount=0,
            comments=[],
            error=f"予期しないエラーが発生しました: {str(e)}",
        )


class PreviewRequest(BaseModel):
    """Request model for data preview."""

    source: str
    limit: int | None = 10


class PreviewResponse(BaseModel):
    """Response model for data preview."""

    success: bool
    comments: list[dict]
    totalCount: int
    error: str | None


@router.post("/admin/plugins/{plugin_id}/preview", dependencies=[Depends(verify_admin_api_key)])
async def preview_data(plugin_id: str, request: PreviewRequest) -> PreviewResponse:
    """
    Preview data from a plugin source.

    Fetches a small sample of data to show the user before importing.
    """
    plugin = PluginRegistry.get_plugin(plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    try:
        # Fetch a small sample
        df = plugin.fetch_data(request.source, max_results=request.limit or 10)

        return PreviewResponse(
            success=True,
            comments=df.head(request.limit or 10).to_dict(orient="records"),
            totalCount=len(df),
            error=None,
        )

    except PluginConfigError as e:
        return PreviewResponse(success=False, comments=[], totalCount=0, error=str(e))
    except ValueError as e:
        return PreviewResponse(success=False, comments=[], totalCount=0, error=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error during preview: {e}")
        return PreviewResponse(
            success=False,
            comments=[],
            totalCount=0,
            error=f"予期しないエラーが発生しました: {str(e)}",
        )
