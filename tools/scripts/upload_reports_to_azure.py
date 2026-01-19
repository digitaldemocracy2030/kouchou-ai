"""
Script to upload existing reports from local filesystem to Azure Blob Storage.

This script:
1. Reads local report files from the server/broadlistening/pipeline/outputs directory
2. Reads the report_status.json file from server/data
3. Uploads these files to Azure Blob Storage with the appropriate structure

Usage:
    python upload_reports_to_azure.py [--test]

Options:
    --test       Run in test mode (doesn't actually upload files)
"""

import json
import os
import sys
import argparse
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
SERVER_DIR = REPO_ROOT / "server"
OUTPUT_DIR = SERVER_DIR / "broadlistening" / "pipeline" / "outputs"
STATUS_FILE = SERVER_DIR / "data" / "report_status.json"

try:
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
except ImportError as e:
    logger.error(f"Error importing Azure libraries: {e}")
    logger.error(
        "Please install required packages: pip install azure-storage-blob azure-identity"
    )
    sys.exit(1)


class AzureBlobUploader:
    """Azure Blob Storage uploader for reports."""

    def __init__(self):
        """Initialize the Azure Blob Storage uploader."""
        self.storage_type = os.environ.get("STORAGE_TYPE", "local")
        self.account_name = os.environ.get("AZURE_BLOB_STORAGE_ACCOUNT_NAME", "")
        self.container_name = os.environ.get("AZURE_BLOB_STORAGE_CONTAINER_NAME", "")

        self.account_url = f"https://{self.account_name}.blob.core.windows.net"

        self.blob_service_client = None
        self.container_client = None

    def check_environment(self):
        """Check if the environment is properly configured for Azure Blob Storage."""
        if self.storage_type != "azure_blob":
            logger.error(
                "STORAGE_TYPE is not set to 'azure_blob'. Please update your .env file."
            )
            return False

        if not self.account_name:
            logger.error(
                "AZURE_BLOB_STORAGE_ACCOUNT_NAME is not set. Please update your .env file."
            )
            return False

        if not self.container_name:
            logger.error(
                "AZURE_BLOB_STORAGE_CONTAINER_NAME is not set. Please update your .env file."
            )
            return False

        return True

    def connect(self):
        """Connect to Azure Blob Storage."""
        try:
            self.blob_service_client = BlobServiceClient(
                account_url=self.account_url,
                credential=DefaultAzureCredential(),
            )
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Azure Blob Storage: {e}")
            return False

    def upload_file(self, local_file_path, remote_blob_path, skip_if_same=True):
        """Upload a file to Azure Blob Storage."""
        try:
            if remote_blob_path.endswith("/"):
                remote_blob_path = remote_blob_path + os.path.basename(local_file_path)
            elif remote_blob_path == "" or remote_blob_path == ".":
                remote_blob_path = os.path.basename(local_file_path)

            blob_client = self.container_client.get_blob_client(remote_blob_path)

            if skip_if_same and blob_client.exists():
                local_file_size = os.path.getsize(local_file_path)

                blob_properties = blob_client.get_blob_properties()
                remote_file_size = blob_properties.size

                if local_file_size == remote_file_size:
                    logger.info(
                        f"同一ファイルが存在します。アップロードをスキップします。パス: '{local_file_path}' -> '{remote_blob_path}'"
                    )
                    return True

            with open(local_file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            logger.info(
                f"ファイルをアップロードしました。パス: '{local_file_path}' -> '{remote_blob_path}'"
            )
            return True
        except Exception as e:
            logger.error(
                f"ファイルのアップロードに失敗しました。パス: '{local_file_path}' -> '{remote_blob_path}' エラー: {str(e)}"
            )
            return False

    def upload_directory(
        self, local_dir_path, remote_dir_prefix, target_suffixes=(), skip_if_same=True
    ):
        """Upload a directory to Azure Blob Storage."""
        try:
            prefix = remote_dir_prefix
            if prefix and not prefix.endswith("/"):
                prefix += "/"

            files_processed = 0
            upload_results = []

            for root, _, files in os.walk(local_dir_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, local_dir_path)
                    remote_blob_path = (
                        prefix + relative_path.replace(os.sep, "/")
                        if prefix
                        else relative_path.replace(os.sep, "/")
                    )

                    if target_suffixes and not any(
                        remote_blob_path.endswith(suffix) for suffix in target_suffixes
                    ):
                        continue

                    files_processed += 1
                    success = self.upload_file(
                        file_path, remote_blob_path, skip_if_same=skip_if_same
                    )
                    upload_results.append(success)

            if files_processed == 0:
                logger.warning(
                    f"アップロード対象のファイルが見つかりませんでした。パス: '{local_dir_path}'"
                )
                return False

            if not all(upload_results):
                logger.error(
                    f"ディレクトリのアップロードに失敗しました。パス: '{local_dir_path}' プレフィックス: '{remote_dir_prefix}'"
                )
                return False

            return True
        except Exception as e:
            logger.error(
                f"ディレクトリのアップロードに失敗しました。パス: '{local_dir_path}' プレフィックス: '{remote_dir_prefix}' エラー: {str(e)}"
            )
            return False


def check_environment():
    """Check if the environment is properly configured for Azure Blob Storage."""
    uploader = AzureBlobUploader()
    return uploader.check_environment()


def upload_reports(test_mode=False):
    """Upload all local reports to Azure Blob Storage."""
    uploader = AzureBlobUploader()

    if not uploader.check_environment():
        return False

    if not test_mode and not uploader.connect():
        return False

    if not OUTPUT_DIR.exists():
        logger.error(f"Output directory not found: {OUTPUT_DIR}")
        return False

    if not STATUS_FILE.exists():
        logger.error(f"Status file not found: {STATUS_FILE}")
        return False

    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            status_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing status file: {e}")
        return False
    except Exception as e:
        logger.error(f"Error reading status file: {e}")
        return False

    if test_mode:
        logger.info("Running in test mode. No files will be uploaded.")
        logger.info(f"Would upload status file: {STATUS_FILE}")
        logger.info(f"Would upload reports from: {OUTPUT_DIR}")
        for slug in status_data:
            logger.info(f"Would upload report: {slug}")
        return True

    logger.info("Uploading status file...")
    status_upload_success = uploader.upload_file(
        str(STATUS_FILE), "status/report_status.json"
    )

    if not status_upload_success:
        logger.error("Failed to upload status file.")
        return False

    logger.info("Status file uploaded successfully.")

    success_count = 0
    total_count = 0

    for slug in status_data:
        total_count += 1
        report_dir = OUTPUT_DIR / slug

        if not report_dir.exists():
            logger.warning(f"Report directory not found for slug: {slug}")
            continue

        logger.info(f"Uploading report: {slug}")

        upload_success = uploader.upload_directory(str(report_dir), f"outputs/{slug}")

        if upload_success:
            success_count += 1
            logger.info(f"Successfully uploaded report: {slug}")
        else:
            logger.error(f"Failed to upload report: {slug}")

    logger.info(f"Uploaded {success_count} out of {total_count} reports.")
    return success_count > 0


def main():
    """Main function to upload reports to Azure Blob Storage."""
    parser = argparse.ArgumentParser(
        description="Upload local reports to Azure Blob Storage"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (don't actually upload files)",
    )
    args = parser.parse_args()

    logger.info("Starting upload of reports to Azure Blob Storage...")

    if upload_reports(args.test):
        logger.info("Upload completed successfully.")
        return 0
    else:
        logger.error("Upload failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
