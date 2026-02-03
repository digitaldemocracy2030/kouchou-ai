import json
import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException

from src.config import settings
from src.schemas.admin_report import ReportDuplicateOverrides, ReportDuplicateRequest
from src.services.report_launcher import launch_report_generation_from_config
from src.services.report_status import add_new_report_to_status_from_config, delete_report_from_status, slug_exists
from src.services.report_sync import ReportSyncService
from src.utils.logger import setup_logger

logger = setup_logger()

LOCK_TTL_SECONDS = 10 * 60
LOCK_DIR_NAME = ".duplicate_locks"

REUSE_ARTIFACTS = (
    "args.csv",
    "relations.csv",
    "embeddings.pkl",
    "hierarchical_clusters.csv",
    "hierarchical_initial_labels.csv",
    "hierarchical_merge_labels.csv",
)


def _lock_path(slug: str) -> Path:
    return settings.REPORT_DIR / LOCK_DIR_NAME / f"{slug}.lock"


def _write_lock(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w") as f:
        payload = {"created_at": time.time(), "pid": os.getpid()}
        json.dump(payload, f)


def _lock_expired(path: Path) -> bool:
    try:
        with open(path) as f:
            payload = json.load(f)
        created_at = float(payload.get("created_at", 0))
    except Exception:
        created_at = 0
    if created_at <= 0:
        try:
            created_at = path.stat().st_mtime
        except Exception:
            created_at = 0
    return (time.time() - created_at) > LOCK_TTL_SECONDS


def _cleanup_partial_artifacts(slug: str) -> None:
    config_path = settings.CONFIG_DIR / f"{slug}.json"
    input_path = settings.INPUT_DIR / f"{slug}.csv"
    output_dir = settings.REPORT_DIR / slug

    if config_path.exists():
        config_path.unlink()
    if input_path.exists():
        input_path.unlink()
    if output_dir.exists():
        shutil.rmtree(output_dir)

    delete_report_from_status(slug)


def acquire_duplicate_lock(slug: str) -> Path:
    lock_path = _lock_path(slug)
    try:
        _write_lock(lock_path)
        return lock_path
    except FileExistsError as err:
        if _lock_expired(lock_path):
            # stale lock: if report exists in status, do not delete artifacts
            if slug_exists(slug):
                try:
                    lock_path.unlink()
                except Exception:
                    pass
                raise HTTPException(status_code=409, detail="newSlug already exists") from err
            # cleanup partial artifacts and retry
            # NOTE: We only do a single retry here by design; high-concurrency duplicate
            # requests are rare in this service, so a minimal safeguard is sufficient.
            _cleanup_partial_artifacts(slug)
            try:
                lock_path.unlink()
            except Exception:
                pass
            _write_lock(lock_path)
            return lock_path
        raise HTTPException(status_code=409, detail="Duplicate in progress") from err


def release_duplicate_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        return
    except Exception as e:
        logger.warning(f"Failed to release duplicate lock: {lock_path} error={e}")


def _slug_exists_anywhere(slug: str) -> bool:
    if slug_exists(slug):
        return True
    if (settings.CONFIG_DIR / f"{slug}.json").exists():
        return True
    if (settings.INPUT_DIR / f"{slug}.csv").exists():
        return True
    if (settings.REPORT_DIR / slug).exists():
        return True
    return False


def _generate_slug(source_slug: str) -> str:
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    base = f"{source_slug}-copy-{date_str}"
    if not _slug_exists_anywhere(base):
        return base
    for i in range(1, 1000):
        candidate = f"{base}-{i}"
        if not _slug_exists_anywhere(candidate):
            return candidate
    raise HTTPException(status_code=409, detail="Failed to generate unique slug")


def _apply_overrides(config: dict, overrides: ReportDuplicateOverrides | None) -> dict:
    if overrides is None:
        return config

    if overrides.question is not None:
        config["question"] = overrides.question
    if overrides.intro is not None:
        config["intro"] = overrides.intro
    if overrides.model is not None:
        config["model"] = overrides.model
    if overrides.provider is not None:
        config["provider"] = overrides.provider
    if overrides.cluster is not None:
        config.setdefault("hierarchical_clustering", {})["cluster_nums"] = overrides.cluster

    if overrides.prompt is not None:
        if overrides.prompt.extraction is not None:
            config.setdefault("extraction", {})["prompt"] = overrides.prompt.extraction
        if overrides.prompt.initial_labelling is not None:
            config.setdefault("hierarchical_initial_labelling", {})["prompt"] = overrides.prompt.initial_labelling
        if overrides.prompt.merge_labelling is not None:
            config.setdefault("hierarchical_merge_labelling", {})["prompt"] = overrides.prompt.merge_labelling
        if overrides.prompt.overview is not None:
            config.setdefault("hierarchical_overview", {})["prompt"] = overrides.prompt.overview

    return config


def _ensure_source_input(slug: str) -> Path:
    input_path = settings.INPUT_DIR / f"{slug}.csv"
    if input_path.exists():
        return input_path

    ReportSyncService().download_input_file(slug)
    if input_path.exists():
        return input_path

    raise HTTPException(status_code=404, detail="Source input file not found")


def _ensure_source_artifacts(slug: str, file_names: tuple[str, ...]) -> None:
    missing = []
    for name in file_names:
        if not (settings.REPORT_DIR / slug / name).exists():
            missing.append(name)

    if not missing:
        return

    ReportSyncService().download_report_artifacts(slug, missing)


def duplicate_report(
    source_slug: str,
    payload: ReportDuplicateRequest,
    user_api_key: str | None = None,
) -> str:
    requested_slug = (payload.new_slug or "").strip()
    new_slug = requested_slug or _generate_slug(source_slug)

    lock_path = acquire_duplicate_lock(new_slug)
    created_any = False
    cleanup_on_failure = True
    try:
        if _slug_exists_anywhere(new_slug):
            raise HTTPException(status_code=409, detail="newSlug already exists")

        config_path = settings.CONFIG_DIR / f"{source_slug}.json"
        if not config_path.exists():
            ReportSyncService().download_all_config_files_from_storage()
        if not config_path.exists():
            raise HTTPException(status_code=404, detail="Source config not found")

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        config["name"] = new_slug
        config["input"] = new_slug
        # Keep source_slug in status only; analysis-core config schema doesn't accept it.
        config = _apply_overrides(config, payload.overrides)

        new_config_path = settings.CONFIG_DIR / f"{new_slug}.json"
        new_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(new_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        created_any = True

        source_input_path = _ensure_source_input(source_slug)
        new_input_path = settings.INPUT_DIR / f"{new_slug}.csv"
        new_input_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_input_path, new_input_path)

        output_dir = settings.REPORT_DIR / new_slug
        output_dir.mkdir(parents=True, exist_ok=True)

        reuse_enabled = payload.reuse.enabled if payload.reuse is not None else True
        if reuse_enabled:
            _ensure_source_artifacts(source_slug, REUSE_ARTIFACTS + ("hierarchical_status.json",))

            source_output_dir = settings.REPORT_DIR / source_slug
            for name in REUSE_ARTIFACTS:
                src = source_output_dir / name
                if src.exists():
                    shutil.copy2(src, output_dir / name)

            status_src = source_output_dir / "hierarchical_status.json"
            if status_src.exists():
                shutil.copy2(status_src, output_dir / "hierarchical_status.json")
            else:
                logger.warning(f"hierarchical_status.json not found for {source_slug}")

        # Always remove overview/result to force regeneration
        for name in ("hierarchical_result.json", "hierarchical_overview.txt"):
            target = output_dir / name
            if target.exists():
                target.unlink()

        add_new_report_to_status_from_config(new_slug, config, source_slug=source_slug)
        cleanup_on_failure = False

        try:
            launch_report_generation_from_config(new_config_path, new_slug, user_api_key)
        except Exception as e:
            # status was created; set to error in launcher and re-raise
            raise HTTPException(status_code=500, detail=f"Failed to start analysis-core: {e}") from e

        return new_slug
    except Exception:
        # Best-effort cleanup on failure only if we created artifacts
        if created_any and cleanup_on_failure:
            _cleanup_partial_artifacts(new_slug)
        raise
    finally:
        release_duplicate_lock(lock_path)
