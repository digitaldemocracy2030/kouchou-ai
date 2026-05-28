#!/usr/bin/env python3
"""
Download canonical report data from Azure Blob Storage into the local filesystem.

This script restores the storage-backed state that the API uses as its canonical
store, instead of scraping public `/reports` endpoints.

Usage:
    python tools/scripts/download_reports_from_azure.py
    python tools/scripts/download_reports_from_azure.py --slug report-slug
"""

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SERVER_DIR = REPO_ROOT / "apps" / "api"

sys.path.insert(0, str(SERVER_DIR))

from src.config import settings  # noqa: E402
from src.services.report_sync import ReportSyncService  # noqa: E402


def download_single_report(report_sync_service: ReportSyncService, slug: str) -> bool:
    """Download one report's input/config/output artifacts from storage."""
    storage_service = report_sync_service.storage_service

    remote_input_file_path = f"{report_sync_service.REMOTE_INPUT_DIR_PREFIX}/{slug}.csv"
    remote_config_file_path = f"{report_sync_service.REMOTE_CONFIG_DIR_PREFIX}/{slug}.json"
    local_input_file_path = settings.INPUT_DIR / f"{slug}.csv"
    local_config_file_path = settings.CONFIG_DIR / f"{slug}.json"

    local_input_file_path.parent.mkdir(parents=True, exist_ok=True)
    local_config_file_path.parent.mkdir(parents=True, exist_ok=True)

    input_success = storage_service.download_file(remote_input_file_path, str(local_input_file_path))
    config_success = storage_service.download_file(remote_config_file_path, str(local_config_file_path))
    report_success = report_sync_service.download_report_artifacts(
        slug, report_sync_service.PRESERVED_REPORT_FILES
    )

    return input_success and config_success and report_success


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download canonical report data from Azure Blob Storage"
    )
    parser.add_argument(
        "--slug",
        help="Download only one report slug instead of the full storage snapshot",
    )
    args = parser.parse_args()

    report_sync_service = ReportSyncService()

    if args.slug:
        success = download_single_report(report_sync_service, args.slug)
        if not success:
            print(f"❌ Failed to download report snapshot for slug: {args.slug}")
            return 1
        print(f"✅ Downloaded storage snapshot for slug: {args.slug}")
    else:
        status_success = report_sync_service.download_status_file_from_storage()
        reports_success = report_sync_service.download_all_report_results_from_storage()
        config_success = report_sync_service.download_all_config_files_from_storage()
        input_success = report_sync_service.download_all_input_files_from_storage()
        success = status_success and reports_success and config_success and input_success
        if not success:
            print("❌ Failed to download one or more storage-backed datasets")
            return 1
        print("✅ Downloaded storage snapshot for status / reports / configs / inputs")

    print(f"status: {settings.DATA_DIR / 'report_status.json'}")
    print(f"reports: {settings.REPORT_DIR}")
    print(f"configs: {settings.CONFIG_DIR}")
    print(f"inputs: {settings.INPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
