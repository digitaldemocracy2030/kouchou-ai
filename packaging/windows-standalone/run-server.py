"""Launcher for the kouchou-ai Windows standalone bundle.

Started by start.bat as:  runtime\python.exe -X utf8 run-server.py

Responsibilities:
  - run from the bundled `app/` directory so `import src...` and the
    broadlistening pipeline paths resolve exactly like in dev,
  - provide safe defaults for required settings if the user has no .env,
  - boot the FastAPI backend with uvicorn,
  - open the browser at the report viewer.

UTF-8 mode (-X utf8) is mandatory: on Japanese Windows the default text
encoding is cp932, which breaks json.load() of the UTF-8 report files
(see tmp-embeddable-poc/FINDINGS.md). start.bat passes -X utf8; this script
also re-checks and warns if it was launched without it.
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path

HOST = os.environ.get("KOUCHOU_HOST", "127.0.0.1")
PORT = int(os.environ.get("KOUCHOU_PORT", "8000"))
BUNDLE_DIR = Path(__file__).resolve().parent
APP_DIR = BUNDLE_DIR / "app"
VIEWER_DIR = BUNDLE_DIR / "viewer"
# The bundle's editable config lives next to start.bat (NOT inside app/, which we chdir into).
BUNDLE_ENV = BUNDLE_DIR / ".env"
# The API owns "/" (healthcheck), so the viewer is served under /viewer
# (built with NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH=/viewer).
VIEWER_PATH = "/viewer/"


def _warn_if_not_utf8() -> None:
    # sys.flags.utf8_mode is 1 when started with -X utf8 or PYTHONUTF8=1
    if getattr(sys.flags, "utf8_mode", 0) != 1:
        print(
            "WARNING: UTF-8 mode is OFF. On Japanese Windows this will cause "
            "cp932 decode errors. Launch via start.bat (python -X utf8).",
            file=sys.stderr,
        )


def _apply_default_env() -> None:
    """Load the bundle's .env, then fill only the still-missing keys with defaults.

    Order matters. The user edits ``dist\\.env`` (next to start.bat) to set real keys
    or switch provider/storage. We must load it FIRST and with ``override=True`` so
    those values land in os.environ before any placeholder defaults; otherwise the
    setdefault placeholders would shadow the user's config (src.config loads dotenv
    with override=False, so an env var already present always wins). We also point
    ``ENV_FILE`` at the .env's absolute path so src.config still finds it after we
    chdir into ``app/`` (the default ``.env`` lookup is cwd-relative).
    """
    from dotenv import load_dotenv

    if BUNDLE_ENV.exists():
        load_dotenv(BUNDLE_ENV, override=True)
        os.environ.setdefault("ENV_FILE", str(BUNDLE_ENV))

    defaults = {
        "ENVIRONMENT": "production",
        "STORAGE_TYPE": "local",
        "ADMIN_API_KEY": "local-admin",
        "PUBLIC_API_KEY": "local-public",
        "OPENAI_API_KEY": "not-needed-for-local-llm",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


def _open_browser_when_ready() -> None:
    """Open the viewer once the server is accepting connections."""
    import socket
    import time

    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    else:
        return
    landing = VIEWER_PATH if VIEWER_DIR.exists() else "/"
    webbrowser.open(f"http://{HOST}:{PORT}{landing}")


def main() -> None:
    _warn_if_not_utf8()
    _apply_default_env()

    if not APP_DIR.exists():
        sys.exit(f"Bundled app directory not found: {APP_DIR}")

    # Make `import src...` resolve and pipeline relative paths behave like dev.
    os.chdir(APP_DIR)
    sys.path.insert(0, str(APP_DIR))

    import uvicorn
    from src.main import app

    # Serve the bundled public-viewer static SPA under /viewer (the API owns "/").
    if VIEWER_DIR.exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/viewer", StaticFiles(directory=str(VIEWER_DIR), html=True), name="viewer")
        landing = VIEWER_PATH
    else:
        print("NOTE: viewer/ not bundled — UI will not be served. Run build.ps1 without -SkipFrontend.")
        landing = "/"

    threading.Thread(target=_open_browser_when_ready, daemon=True).start()

    print(f"kouchou-ai standalone starting on http://{HOST}:{PORT}{landing} ...")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
