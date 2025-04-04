import json
import threading

from src.config import settings
from src.schemas.admin_report import ReportInput
from src.schemas.report import Report

STATE_FILE = settings.DATA_DIR / "report_status.json"
_lock = threading.RLock()
_report_status = {}


def load_status() -> None:
    global _report_status
    try:
        with open(STATE_FILE) as f:
            _report_status = json.load(f)
    except FileNotFoundError:
        _report_status = {}


def load_status_as_reports() -> list[Report]:
    global _report_status
    try:
        with open(STATE_FILE) as f:
            _report_status = json.load(f)
    except FileNotFoundError:
        _report_status = {}
    except json.JSONDecodeError:
        _report_status = {}
    return [Report(**report) for report in _report_status.values()]


def save_status() -> None:
    with _lock:
        with open(STATE_FILE, "w") as f:
            json.dump(_report_status, f, indent=4, ensure_ascii=False)


def add_new_report_to_status(report_input: ReportInput) -> None:
    with _lock:
        _report_status[report_input.input] = {
            "slug": report_input.input,
            "status": "processing",
            "title": report_input.question,
            "description": report_input.intro,
            "is_pubcom": report_input.is_pubcom,
            "is_public": True,  # デフォルトは公開状態
        }
        save_status()


def set_status(slug: str, status: str) -> None:
    with _lock:
        if slug not in _report_status:
            raise ValueError(f"slug {slug} not found in report status")
        _report_status[slug]["status"] = status
        save_status()


def get_status(slug: str) -> str:
    with _lock:
        return _report_status.get(slug, {}).get("status", "undefined")


def toggle_report_public_state(slug: str) -> bool:
    with _lock:
        if slug not in _report_status:
            raise ValueError(f"slug {slug} not found in report status")
        _report_status[slug]["is_public"] = not _report_status[slug].get("is_public", True)
        save_status()
        return _report_status[slug]["is_public"]
