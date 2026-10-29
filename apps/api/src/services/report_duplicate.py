import csv
import json
import os
import shutil
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException

from src.config import settings
from src.schemas.admin_report import ReportDuplicateOverrides, ReportDuplicateRequest
from src.schemas.report_config import ReportConfig
from src.services import report_status
from src.services.analysis_config import prune_config_for_mode
from src.services.model_catalog import EMBEDDING_KIND, models_for_provider
from src.services.report_launcher import disable_umap_model_saving, launch_report_generation_from_config
from src.services.report_status import add_new_report_to_status_from_config, delete_report_from_status, slug_exists
from src.services.report_sync import ReportSyncService
from src.utils.logger import setup_logger
from src.utils.slug_utils import validate_slug

logger = setup_logger()

LOCK_TTL_SECONDS = 10 * 60
# 複製元の入力 CSV を取得できず、抽出済みの意見から入力を作り直したことを示す status の警告コード
SOURCE_INPUT_RECONSTRUCTED_WARNING = "source_input_reconstructed"
LOCK_DIR_NAME = ".duplicate_locks"

REUSE_ARTIFACTS = (
    "args.csv",
    "relations.csv",
    "embeddings.pkl",
    "hierarchical_clusters.csv",
    "hierarchical_initial_labels.csv",
    "hierarchical_merge_labels.csv",
)


def _write_reuse_status(
    status_src: Path,
    status_dest: Path,
    renamed_input: tuple[str, str] | None = None,
) -> None:
    """複製先に、元レポートの完了済みジョブだけを引き継いだ status ファイルを書く

    元の status（status=completed）をそのままコピーすると、analysis-core が running に
    書き換えるまでの間に進捗ポーリングが completed を受け取り、止まってしまう。
    analysis-core のスキップ判定に必要な completed_jobs / previously_completed_jobs だけを
    残し、status は pending にする（running にすると lock_until の判定にかかる）。

    完了記録の global_params.input には実行時の入力名が残り、analysis-core はこれが config の
    input と違うと抽出から全段を再実行する。renamed_input=(複製元の入力名, 複製先の入力名) を
    渡すと、複製元の入力名で記録されたジョブの input を複製先の入力名に読み替える。入力 CSV を
    そのままコピーした（中身が同じ）場合に限って渡すこと。global_params の無い古い形式の記録は
    analysis-core が比較しないので、そのまま残す。
    """
    try:
        with open(status_src, encoding="utf-8") as f:
            source_status = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read {status_src}; copying as is: {e}")
        shutil.copy2(status_src, status_dest)
        return

    reuse_status = {
        "status": "pending",
        "completed_jobs": source_status.get("completed_jobs", []),
        "previously_completed_jobs": source_status.get("previously_completed_jobs", []),
    }
    if renamed_input is not None:
        source_input, new_input = renamed_input
        for key in ("completed_jobs", "previously_completed_jobs"):
            for job in reuse_status[key] or []:
                global_params = job.get("global_params") if isinstance(job, dict) else None
                if isinstance(global_params, dict) and global_params.get("input") == source_input:
                    global_params["input"] = new_input
    with open(status_dest, "w", encoding="utf-8") as f:
        json.dump(reuse_status, f, ensure_ascii=False, indent=2)


def _lock_path(slug: str) -> Path:
    return settings.REPORT_DIR / LOCK_DIR_NAME / f"{slug}.lock"


def _write_lock(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        payload = {"created_at": time.time(), "pid": os.getpid()}
        json.dump(payload, f)


def _lock_expired(path: Path) -> bool:
    try:
        with open(path, encoding="utf-8") as f:
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


def slug_exists_anywhere(slug: str, include_input: bool = True) -> bool:
    if slug_exists(slug):
        return True
    if (settings.CONFIG_DIR / f"{slug}.json").exists():
        return True
    if include_input and (settings.INPUT_DIR / f"{slug}.csv").exists():
        return True
    if (settings.REPORT_DIR / slug).exists():
        return True
    return False


class ReportIdInUseError(Exception):
    """入力 CSV を保存・削除しようとした ID が、既存のレポートで使われていることを表す例外"""

    def __init__(self, slug: str):
        super().__init__(f"ID {slug} は既存のレポートで使われています。別のIDを指定してください")
        self.slug = slug


@contextmanager
def guard_unused_report_id(slug: str) -> Iterator[None]:
    """既存レポートの ID でないことを確かめ、その判定を保ったまま入力 CSV の保存・削除を行わせる

    レポート作成（launch_report_generation）は report_status のロック内で status に登録してから
    入力 CSV を書く。判定から保存・削除までを同じロックで囲むと、作成と交差しても
    「保存・削除のあとに作成が登録して入力 CSV を書き直す」か「作成の登録後に判定して拒否する」の
    どちらかになり、作成したレポートの入力 CSV を上書き・削除しない。
    外部からの取得など時間のかかる処理は、このブロックの外で行うこと。
    作成前の取り込みで作られる inputs/<id>.csv だけの状態は、再取り込み・クリアを許すため衝突に含めない。

    Raises:
        ReportIdInUseError: 既存のレポートで使われている ID の場合
    """
    with report_status._lock:
        if slug_exists_anywhere(slug, include_input=False):
            raise ReportIdInUseError(slug)
        yield


def _load_report_result(slug: str) -> dict:
    """Load hierarchical_result.json for a slug, downloading it from storage if needed."""
    result_path = settings.REPORT_DIR / slug / "hierarchical_result.json"
    if not result_path.exists():
        ReportSyncService().download_report_artifacts(slug, ("hierarchical_result.json",))
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Source report result not found")
    try:
        with open(result_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read source report result: {e}") from e


def _build_analysis_core_config_from_embedded_config(embedded_config: dict) -> dict:
    """Build a valid analysis-core config dict from embedded config in hierarchical_result.json."""
    try:
        parsed = ReportConfig(**embedded_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid source embedded config: {e}") from e

    config = parsed.model_dump()

    # Keep enable_source_link if available (analysis-core supports it, but our ReportConfig schema may ignore it).
    enable_source_link = embedded_config.get("enable_source_link")
    if isinstance(enable_source_link, bool):
        config["enable_source_link"] = enable_source_link

    # Keep the source embedding model (ReportConfig has no embedding field, so model_dump() drops it).
    # 引き継がないと複製先が既定モデルで embeddings を再生成し、異なるベクトル空間になる。
    # model だけ取り出し、normalize 済みの source_code サブフィールドは再導入しない
    # （analysis-core の step 別オプション検証で弾かれるため）。
    embedding = embedded_config.get("embedding")
    if isinstance(embedding, dict) and isinstance(embedding.get("model"), str):
        config["embedding"] = {"model": embedding["model"]}

    return config


def _write_input_csv_from_arguments(arguments: list, output_path: Path) -> int:
    """Create an input CSV from hierarchical_result.json 'arguments' as a fallback."""
    rows: list[dict[str, str]] = []
    for i, arg in enumerate(arguments):
        if not isinstance(arg, dict):
            continue
        text = arg.get("argument")
        if not isinstance(text, str) or not text.strip():
            continue
        arg_id = arg.get("arg_id") or arg.get("arg-id") or str(i)
        url = arg.get("url")
        rows.append(
            {
                "comment-id": str(arg_id),
                "comment-body": text,
                "source": "reuse-argument",
                "url": str(url) if isinstance(url, str) else "",
            }
        )

    if not rows:
        raise HTTPException(status_code=404, detail="Source input file not found (no arguments to reconstruct input)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["comment-id", "comment-body", "source", "url"])
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def _generate_slug(source_slug: str) -> str:
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    base = f"{source_slug}-copy-{date_str}"
    if not slug_exists_anywhere(base):
        return base
    for i in range(1, 1000):
        candidate = f"{base}-{i}"
        if not slug_exists_anywhere(candidate):
            return candidate
    raise HTTPException(status_code=409, detail="Failed to generate unique slug")


def _apply_overrides(config: dict, overrides: ReportDuplicateOverrides | None) -> dict:
    if overrides is None:
        return config

    source_provider = config.get("provider") or "openai"

    if overrides.question is not None:
        config["question"] = overrides.question
    if overrides.intro is not None:
        config["intro"] = overrides.intro
    if overrides.model is not None:
        config["model"] = overrides.model
    if overrides.embedding_model is not None:
        config.setdefault("embedding", {})["model"] = overrides.embedding_model
    if overrides.provider is not None:
        config["provider"] = overrides.provider
    if overrides.workers is not None:
        config.setdefault("extraction", {})["workers"] = overrides.workers
        # 作成時 (report_launcher._build_config) と同じく、LLM を並列に呼ぶ初期・統合ラベリングにも
        # 反映する。ラベリングのセクションが無い llm_grouping では、セクションを新しく作らない。
        # hierarchical_aggregation.sampling_num は作成時に workers と同じ値を入れているが、
        # 並列数ではなく集計のサンプル数で、aggregation の再実行判定 params にも入っているため連動させない。
        for section in ("hierarchical_initial_labelling", "hierarchical_merge_labelling"):
            if isinstance(config.get(section), dict):
                config[section]["workers"] = overrides.workers
    if overrides.is_pubcom is not None:
        config["is_pubcom"] = overrides.is_pubcom
    if overrides.enable_source_link is not None:
        config["enable_source_link"] = overrides.enable_source_link
    if overrides.enable_original_comments is not None:
        config["enable_original_comments"] = overrides.enable_original_comments
    if overrides.is_embedded_at_local is not None:
        config["is_embedded_at_local"] = overrides.is_embedded_at_local
    if overrides.local_llm_address is not None:
        config["local_llm_address"] = overrides.local_llm_address
    if overrides.cluster is not None:
        config.setdefault("hierarchical_clustering", {})["cluster_nums"] = overrides.cluster
    if overrides.workers is not None and config.get("analysis_mode") == "llm_grouping":
        # 作成時 (report_launcher._build_config) と同じく、LLM 直接グルーピングの割当にも並列数を渡す。
        # hierarchical の config には llm_grouping セクションを作らない（analysis-core の検証で弾かれる）。
        llm_grouping = config.get("llm_grouping") if isinstance(config.get("llm_grouping"), dict) else {}
        config["llm_grouping"] = {**llm_grouping, "workers": overrides.workers}

    if overrides.prompt is not None:
        if overrides.prompt.extraction is not None:
            config.setdefault("extraction", {})["prompt"] = overrides.prompt.extraction
        if overrides.prompt.initial_labelling is not None:
            config.setdefault("hierarchical_initial_labelling", {})["prompt"] = overrides.prompt.initial_labelling
        if overrides.prompt.merge_labelling is not None:
            config.setdefault("hierarchical_merge_labelling", {})["prompt"] = overrides.prompt.merge_labelling
        if overrides.prompt.overview is not None:
            config.setdefault("hierarchical_overview", {})["prompt"] = overrides.prompt.overview

    _resolve_embedding_for_provider_change(config, source_provider, overrides)
    return config


# 埋め込み API を持たない（OpenRouter）か、選べる埋め込みモデルが無い（local）プロバイダ。
# 新規作成画面と同じく、サーバ内埋め込み（is_embedded_at_local）を求める。
PROVIDERS_REQUIRING_LOCAL_EMBEDDING = ("openrouter", "local")


def _resolve_embedding_for_provider_change(
    config: dict, source_provider: str, overrides: ReportDuplicateOverrides
) -> None:
    """プロバイダを替えた複製で、複製元の埋め込みモデルを新しいプロバイダで使えるものに揃える

    複製は複製元の embedding.model を引き継ぐ（同じベクトル空間を保つため）。プロバイダを替えると
    抽出から再実行され、埋め込みもやり直しになるが、複製元のモデルのままだと新しいプロバイダで使えず
    （例: gemini-embedding-001 を OpenAI に送る）、抽出を課金し終えた後に失敗する。
    プロバイダを替えない複製と、埋め込みモデルを明示した複製には手を入れない。
    """
    new_provider = config.get("provider") or "openai"
    if new_provider == source_provider or overrides.embedding_model is not None:
        return

    if new_provider in PROVIDERS_REQUIRING_LOCAL_EMBEDDING:
        if not config.get("is_embedded_at_local"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"AI プロバイダを {new_provider} に替えるときは、サーバ内埋め込み（is_embedded_at_local）を"
                    "有効にしてください。このプロバイダでは埋め込みモデルを選べません"
                    "（管理画面では『再利用』ページで切り替えられます）。"
                ),
            )
        return

    if new_provider == "azure":
        # Azure はサーバー設定の埋め込みデプロイを使う。新規作成と同じく embedding セクションを省き、
        # 複製元の別プロバイダのモデル名を成果物に残さない。
        config.pop("embedding", None)
        return

    candidates = [
        row["value"]
        for row in models_for_provider(new_provider, kind=EMBEDDING_KIND)
        if row.get("available", True) and not row.get("deprecated")
    ]
    if not candidates:
        return
    embedding = config.get("embedding") if isinstance(config.get("embedding"), dict) else {}
    if embedding.get("model") in candidates:
        return
    # 新規作成画面の初期選択と同じく、カタログで先頭の利用可能なモデルを使う
    config["embedding"] = {**embedding, "model": candidates[0]}


def _ensure_source_input(slug: str) -> Path:
    input_path = settings.INPUT_DIR / f"{slug}.csv"
    if input_path.exists():
        return input_path

    ReportSyncService().download_input_file(slug)
    if input_path.exists():
        return input_path

    raise HTTPException(status_code=404, detail="Source input file not found")


def _is_usable_artifact(path: Path) -> bool:
    """中身のある成果物ファイルかどうか（0 バイトはダウンロードの失敗跡などとみなし、無いものとして扱う）"""
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _ensure_source_artifacts(slug: str, file_names: tuple[str, ...]) -> set[str]:
    """複製元の成果物のうち足りないものをストレージから取得し、再利用できるファイル名を返す

    無いファイルと 0 バイトのファイルを取得し直す。取得に失敗したもの・取得しても空のものは
    返り値に含めない（呼び出し側はそれをコピーせず、analysis-core に再計算させる）。
    """
    source_dir = settings.REPORT_DIR / slug
    missing = [name for name in file_names if not _is_usable_artifact(source_dir / name)]

    if missing:
        downloaded = ReportSyncService().download_report_artifacts(slug, missing)
        still_missing = [name for name in missing if not _is_usable_artifact(source_dir / name)]
        if still_missing:
            logger.warning(
                "複製元の成果物を取得できなかったため、再利用せずに再計算します",
                slug=slug,
                files=still_missing,
                download_succeeded=bool(downloaded),
            )

    return {name for name in file_names if _is_usable_artifact(source_dir / name)}


def duplicate_report(
    source_slug: str,
    payload: ReportDuplicateRequest,
    user_api_key: str | None = None,
) -> str:
    requested_slug = (payload.new_slug or "").strip()
    new_slug = requested_slug or _generate_slug(source_slug)
    validate_slug(new_slug)

    lock_path = acquire_duplicate_lock(new_slug)
    created_any = False
    cleanup_on_failure = True
    try:
        if slug_exists_anywhere(new_slug):
            raise HTTPException(status_code=409, detail="newSlug already exists")

        source_result: dict | None = None

        config_path = settings.CONFIG_DIR / f"{source_slug}.json"
        if not config_path.exists():
            ReportSyncService().download_all_config_files_from_storage()
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
        else:
            source_result = _load_report_result(source_slug)
            embedded_config = source_result.get("config")
            if not isinstance(embedded_config, dict):
                raise HTTPException(status_code=404, detail="Source config not found")
            config = _build_analysis_core_config_from_embedded_config(embedded_config)

        new_input_path = settings.INPUT_DIR / f"{new_slug}.csv"
        new_input_path.parent.mkdir(parents=True, exist_ok=True)

        source_input_path = settings.INPUT_DIR / f"{source_slug}.csv"
        if not source_input_path.exists():
            ReportSyncService().download_input_file(source_slug)

        input_limit_override: int | None = None
        input_copied = source_input_path.exists()
        if input_copied:
            shutil.copy2(source_input_path, new_input_path)
        else:
            if source_result is None:
                source_result = _load_report_result(source_slug)
            input_limit_override = _write_input_csv_from_arguments(
                source_result.get("arguments") or [],
                new_input_path,
            )
            # 旧形式レポートの救済として続けるが、元の入力とは別物になる（意見を再抽出し、属性列が無く、
            # 件数は回答数ではなく意見数になる）。ファイルが無いのか取得に失敗したのかは区別できないので、
            # 黙らずにログと status の警告に残す。
            logger.warning(
                f"複製元 {source_slug} の入力 CSV を取得できなかったため、抽出済みの意見 {input_limit_override} 件から"
                f"入力を作り直して {new_slug} を作成します。属性と回答数は引き継がれません"
            )
        created_any = True

        config["name"] = new_slug
        config["input"] = new_slug
        # v2.1.0 より前に作ったレポートの config には provider が無い。管理画面は provider を
        # 「無ければ openai」とみなして override を送らないので、ここで同じ既定値を補う。
        if not config.get("provider"):
            config["provider"] = "openai"
        # Keep source_slug in status only; analysis-core config schema doesn't accept it.
        config = _apply_overrides(config, payload.overrides)
        if input_limit_override is not None:
            config.setdefault("extraction", {})["limit"] = input_limit_override
        # 新規作成と同じく、Web 経路では使わない umap_model.pkl を保存させない。
        # 複製元の config ファイル（この設定より前に作ったレポートのもの）も、
        # 埋め込み config から作った config も、ここで 1 回だけ設定する。
        config = disable_umap_model_saving(config)

        # 複製元 config は (a) 既存 config ファイル、(b) hierarchical_result.json 埋め込みの
        # normalize 済み config（この場合 llm_grouping が値入り dict で混入する）のいずれか。
        # どちらの経路でも analysis_mode 非該当セクションが残りうるため、analysis-core に渡す
        # 直前でモード別に prune する。
        config = prune_config_for_mode(config)

        new_config_path = settings.CONFIG_DIR / f"{new_slug}.json"
        new_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(new_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        output_dir = settings.REPORT_DIR / new_slug
        output_dir.mkdir(parents=True, exist_ok=True)

        reuse_enabled = payload.reuse.enabled if payload.reuse is not None else True
        if reuse_enabled:
            usable = _ensure_source_artifacts(source_slug, REUSE_ARTIFACTS + ("hierarchical_status.json",))

            source_output_dir = settings.REPORT_DIR / source_slug
            for name in REUSE_ARTIFACTS:
                if name in usable:
                    shutil.copy2(source_output_dir / name, output_dir / name)

            status_src = source_output_dir / "hierarchical_status.json"
            if "hierarchical_status.json" in usable:
                # 入力 CSV をそのままコピーした場合だけ、記録上の入力名を新しい slug に読み替える。
                # arguments から作り直した入力は中身が違うので、抽出からやり直させる。
                renamed_input = (source_slug, new_slug) if input_copied else None
                _write_reuse_status(status_src, output_dir / "hierarchical_status.json", renamed_input)
            else:
                logger.warning(f"hierarchical_status.json not found for {source_slug}")

        # Always remove overview/result to force regeneration
        for name in ("hierarchical_result.json", "hierarchical_overview.txt"):
            target = output_dir / name
            if target.exists():
                target.unlink()

        add_new_report_to_status_from_config(new_slug, config, source_slug=source_slug)
        if not input_copied:
            report_status.add_report_warning(new_slug, SOURCE_INPUT_RECONSTRUCTED_WARNING)
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
            try:
                _cleanup_partial_artifacts(new_slug)
            except Exception as cleanup_error:
                logger.warning(
                    "Failed to cleanup partial artifacts",
                    slug=new_slug,
                    error=str(cleanup_error),
                )
        raise
    finally:
        release_duplicate_lock(lock_path)
