"""
Script to upload existing reports from local filesystem to Azure Blob Storage.

This script:
1. Reads local report files from the apps/api/broadlistening/pipeline/outputs directory
2. Reads local config files from the apps/api/broadlistening/pipeline/configs directory
3. Reads local input files from the apps/api/broadlistening/pipeline/inputs directory
4. Reads the report_status.json file from apps/api/data
5. Uploads these files to Azure Blob Storage with the appropriate structure

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
REPO_ROOT = SCRIPT_DIR.parent.parent
SERVER_DIR = REPO_ROOT / "apps" / "api"
OUTPUT_DIR = SERVER_DIR / "broadlistening" / "pipeline" / "outputs"
CONFIG_DIR = SERVER_DIR / "broadlistening" / "pipeline" / "configs"
INPUT_DIR = SERVER_DIR / "broadlistening" / "pipeline" / "inputs"
STATUS_FILE = SERVER_DIR / "data" / "report_status.json"
PRESERVED_REPORT_FILES = (
    ".json",
    "final_result_with_comments.csv",
    "embeddings.pkl",
    "hierarchical_initial_labels.csv",
    "hierarchical_merge_labels.csv",
    "hierarchical_result.json",
    "args.csv",
    "hierarchical_clusters.csv",
    "relations.csv",
    "hierarchical_overview.txt",
)

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
    """Upload all local storage-backed report data to Azure Blob Storage."""
    uploader = AzureBlobUploader()

    if not uploader.check_environment():
        return False

    if not test_mode and not uploader.connect():
        return False

    if not OUTPUT_DIR.exists():
        logger.error(f"Output directory not found: {OUTPUT_DIR}")
        return False

    if not CONFIG_DIR.exists():
        logger.error(f"Config directory not found: {CONFIG_DIR}")
        return False

    if not INPUT_DIR.exists():
        logger.error(f"Input directory not found: {INPUT_DIR}")
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
        logger.info(f"Would upload reports from: {OUTPUT_DIR} -> outputs/")
        logger.info(f"Would upload configs from: {CONFIG_DIR} -> configs/")
        logger.info(f"Would upload inputs from: {INPUT_DIR} -> inputs/")
        logger.info(f"Status contains {len(status_data)} report entries.")
        return True

    logger.info("Uploading status file...")
    status_upload_success = uploader.upload_file(
        str(STATUS_FILE), "status/report_status.json"
    )

    if not status_upload_success:
        logger.error("Failed to upload status file.")
        return False

    logger.info("Status file uploaded successfully.")

    upload_results = [status_upload_success]

    logger.info("Uploading report outputs...")
    reports_upload_success = uploader.upload_directory(
        str(OUTPUT_DIR), "outputs", target_suffixes=PRESERVED_REPORT_FILES
    )
    upload_results.append(reports_upload_success)

    logger.info("Uploading configs...")
    config_upload_success = uploader.upload_directory(
        str(CONFIG_DIR), "configs", target_suffixes=(".json",)
    )
    upload_results.append(config_upload_success)

    logger.info("Uploading inputs...")
    input_upload_success = uploader.upload_directory(
        str(INPUT_DIR), "inputs", target_suffixes=(".csv",)
    )
    upload_results.append(input_upload_success)

    if not all(upload_results):
        logger.error("One or more storage-backed datasets failed to upload.")
        return False

    logger.info(f"Uploaded storage-backed data for {len(status_data)} report entries.")
    return True


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
