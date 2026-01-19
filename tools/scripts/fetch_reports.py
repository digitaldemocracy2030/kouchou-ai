#!/usr/bin/env python3
"""
Script to fetch reports from an existing API server and save them to a new environment.

This script:
1. Fetches all report slugs from GET /reports
2. Fetches individual report results from GET /reports/{slug}
3. Creates directories for each slug under outputs/
4. Saves the result data in the corresponding slug directory
5. Updates ./server/data/report_status.json with the appropriate information

Usage:
    python fetch_reports.py [--test] [--api-url URL]

Options:
    --test       Run in test mode with mock data
    --api-url    API base URL (default: https://api.greenglacier-5bc2e6c1.japaneast.azurecontainerapps.io)
"""

import json
import os
import sys
import argparse
from pathlib import Path
import requests
import getpass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default configuration
API_KEY = os.environ.get("PUBLIC_API_KEY", "")

# Paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = REPO_ROOT / "server" / "broadlistening" / "pipeline" / "outputs"
STATUS_FILE = REPO_ROOT / "server" / "data" / "report_status.json"


def ensure_directories():
    """Ensure necessary directories exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_reports():
    """Fetch all reports from the API."""
    url = f"{API_BASE_URL}/reports"
    headers = {"x-api-key": API_KEY}

    try:
        print(
            f"Sending request to {url} with API key: {API_KEY[:3]}..."
            if API_KEY
            else "No API key provided"
        )
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching reports: {e}")
        if e.response.status_code == 401:
            print("Authentication failed. Please check your API key.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}")
        sys.exit(1)


def get_report_result(slug):
    """Fetch a specific report result by slug."""
    url = f"{API_BASE_URL}/reports/{slug}"
    headers = {"x-api-key": API_KEY}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching report {slug}: {e}")
        if e.response.status_code == 401:
            print("Authentication failed. Please check your API key.")
        elif e.response.status_code == 404:
            print(f"Report {slug} not found.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}")
        return None


def save_report_result(slug, result):
    """Save report result to the appropriate directory."""
    # Create directory for the slug
    slug_dir = OUTPUT_DIR / slug
    slug_dir.mkdir(exist_ok=True)

    # Save result as hierarchical_result.json
    result_file = slug_dir / "hierarchical_result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Saved report result for {slug} to {result_file}")
    return True


def update_report_status(reports):
    """Update the report_status.json file with report information."""
    # Load existing status file if it exists
    status_data = {}
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                status_data = json.load(f)
        except json.JSONDecodeError:
            print(
                f"Warning: Could not parse existing {STATUS_FILE}. Creating new file."
            )

    # Update status data with reports
    for report in reports:
        slug = report["slug"]
        status_data[slug] = {
            "slug": slug,
            "status": "ready",  # All fetched reports are ready
            "title": report["title"],
            "description": report["description"],
        }

    # Save updated status file
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=4)

    print(f"Updated report status in {STATUS_FILE}")


def get_mock_reports():
    """Return mock reports for testing."""
    return [
        {
            "slug": "test-report-1",
            "title": "テストレポート1",
            "description": "テスト用のレポート説明1",
            "status": "ready",
        },
        {
            "slug": "test-report-2",
            "title": "テストレポート2",
            "description": "テスト用のレポート説明2",
            "status": "ready",
        },
    ]


def get_mock_report_result(slug):
    """Return mock report result for testing."""
    return {
        "title": f"テストレポート {slug}",
        "description": f"{slug}のテスト用レポート結果",
        "clusters": [
            {
                "id": "cluster-1",
                "label": "クラスター1",
                "description": "クラスター1の説明",
            }
        ],
        "arguments": [
            {"id": "arg-1", "text": "テスト意見1", "cluster_id": "cluster-1"}
        ],
    }


def main():
    """Main function to fetch and save reports."""
    global API_KEY, API_BASE_URL

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Fetch reports from API and save them locally"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run in test mode with mock data"
    )
    parser.add_argument(
        "--api-url",
        help="API base URL (example: https://api.*****.japaneast.azurecontainerapps.io)",
        required=True,
    )
    args = parser.parse_args()

    # Set API base URL from command line argument
    API_BASE_URL = args.api_url

    # Test mode uses mock data
    if args.test:
        print("Running in test mode with mock data...")
        reports = get_mock_reports()
        ensure_directories()
    else:
        # Normal mode requires API key
        if not API_KEY:
            print("PUBLIC_API_KEY environment variable is not set in .env file.")
            API_KEY = getpass.getpass("Please enter the API key: ")
            if not API_KEY:
                print("Error: API key is required.")
                sys.exit(1)

        print(f"Fetching reports from {API_BASE_URL}...")
        ensure_directories()

        try:
            # Get all reports
            reports = get_reports()
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    print(f"Found {len(reports)} reports")

    # Process each report
    successful_reports = []
    for report in reports:
        slug = report["slug"]
        print(f"Processing report: {slug} - {report['title']}")

        # Get report result (mock or real)
        if args.test:
            result = get_mock_report_result(slug)
        else:
            result = get_report_result(slug)

        if result:
            # Save report result
            if save_report_result(slug, result):
                successful_reports.append(report)

    # Update report status
    if successful_reports:
        update_report_status(successful_reports)
        print(f"Successfully processed {len(successful_reports)} reports")
    else:
        print("No reports were successfully processed")


if __name__ == "__main__":
    main()
