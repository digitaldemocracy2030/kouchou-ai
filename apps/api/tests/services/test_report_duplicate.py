import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def test_duplicate_report_reuses_workflow_artifacts_and_launches_from_config(monkeypatch, tmp_path):
    from src.schemas.admin_report import ReportDuplicateOverrides, ReportDuplicateRequest, ReportDuplicateReuse
    from src.services import report_duplicate

    source_slug = "source"
    new_slug = "copy"

    report_dir = tmp_path / "reports"
    config_dir = tmp_path / "configs"
    input_dir = tmp_path / "inputs"
    (report_dir / source_slug).mkdir(parents=True)
    config_dir.mkdir(parents=True)
    input_dir.mkdir(parents=True)

    monkeypatch.setattr(report_duplicate.settings, "REPORT_DIR", report_dir)
    monkeypatch.setattr(report_duplicate.settings, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(report_duplicate.settings, "INPUT_DIR", input_dir)

    source_config = {
        "name": source_slug,
        "input": source_slug,
        "question": "Source title",
        "intro": "Source description",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "extraction": {
            "workers": 2,
            "prompt": "extract",
        },
        "hierarchical_clustering": {
            "cluster_nums": [2, 4],
        },
    }
    (config_dir / f"{source_slug}.json").write_text(json.dumps(source_config), encoding="utf-8")
    (input_dir / f"{source_slug}.csv").write_text("comment-id,comment-body\n1,hello\n", encoding="utf-8")

    for name in report_duplicate.REUSE_ARTIFACTS:
        (report_dir / source_slug / name).write_text(name, encoding="utf-8")
    # analysis-core は完了記録に実行時の input などを global_params として残す。
    # global_params の無い記録は、それより前の版で書かれた status にある形式。
    global_params = {
        "input": source_slug,
        "question": "Source title",
        "intro": "Source description",
        "is_pubcom": None,
        "enable_source_link": None,
    }
    (report_dir / source_slug / "hierarchical_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "completed_jobs": [
                    {"step": "extraction", "global_params": global_params},
                    {"step": "embedding", "global_params": global_params},
                ],
                "previously_completed_jobs": [
                    {"step": "hierarchical_clustering", "global_params": global_params},
                    {"step": "hierarchical_initial_labelling"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (report_dir / source_slug / "hierarchical_result.json").write_text("{}", encoding="utf-8")
    (report_dir / source_slug / "hierarchical_overview.txt").write_text("overview", encoding="utf-8")

    launched = {}
    status_calls = []

    monkeypatch.setattr(report_duplicate, "slug_exists", lambda slug: False)
    monkeypatch.setattr(report_duplicate, "validate_slug", lambda slug: None)
    monkeypatch.setattr(
        report_duplicate,
        "add_new_report_to_status_from_config",
        lambda slug, config, source_slug=None: status_calls.append((slug, config, source_slug)),
    )
    monkeypatch.setattr(
        report_duplicate,
        "launch_report_generation_from_config",
        lambda config_path, slug, user_api_key=None: launched.update(
            {
                "config_path": config_path,
                "slug": slug,
                "user_api_key": user_api_key,
            }
        ),
    )

    payload = ReportDuplicateRequest(
        new_slug=new_slug,
        overrides=ReportDuplicateOverrides(question="Copied title"),
        reuse=ReportDuplicateReuse(enabled=True),
    )

    result = report_duplicate.duplicate_report(source_slug, payload, user_api_key="test-key")

    new_config_path = config_dir / f"{new_slug}.json"
    new_input_path = input_dir / f"{new_slug}.csv"
    new_output_dir = report_dir / new_slug

    assert result == new_slug
    assert new_config_path.exists()
    assert new_input_path.exists()
    assert launched == {
        "config_path": new_config_path,
        "slug": new_slug,
        "user_api_key": "test-key",
    }

    written_config = json.loads(new_config_path.read_text(encoding="utf-8"))
    assert written_config["name"] == new_slug
    assert written_config["input"] == new_slug
    assert written_config["question"] == "Copied title"
    assert written_config["intro"] == "Source description"

    for name in report_duplicate.REUSE_ARTIFACTS:
        assert (new_output_dir / name).exists(), f"{name} should be copied for reuse"
    copied_status = json.loads((new_output_dir / "hierarchical_status.json").read_text(encoding="utf-8"))
    assert copied_status["completed_jobs"][0]["step"] == "extraction"
    assert copied_status["previously_completed_jobs"][0]["step"] == "hierarchical_clustering"
    # 入力 CSV は中身をそのままコピーしたので、記録上の入力名も新しい slug に読み替える。
    # 読み替えないと analysis-core が input の変更とみなし、抽出から全段を再実行する。
    copied_jobs = copied_status["completed_jobs"] + copied_status["previously_completed_jobs"]
    assert [job.get("global_params", {}).get("input") for job in copied_jobs] == [new_slug, new_slug, new_slug, None]
    # input 以外の記録は変えず、global_params の無い記録にも足さない
    assert copied_status["completed_jobs"][0]["global_params"]["question"] == "Source title"
    assert "global_params" not in copied_status["previously_completed_jobs"][1]
    # 元レポートの completed をそのまま引き継ぐと、新しいカードの進捗ポーリングが即座に止まる
    assert copied_status["status"] != "completed"
    assert not copied_status.get("current_job")
    assert not (new_output_dir / "hierarchical_result.json").exists()
    assert not (new_output_dir / "hierarchical_overview.txt").exists()

    assert status_calls == [(new_slug, written_config, source_slug)]


def test_build_analysis_core_config_preserves_embedding_model():
    """埋め込み config フォールバック経路でも source の embedding.model を引き継ぐ。

    config ファイルが無く hierarchical_result.json 埋め込み config から複製する時、
    embedding section が落ちると複製先が既定モデル(text-embedding-3-small)で
    embeddings を再生成し、異なるベクトル空間になってしまう回帰を防ぐ。
    normalize 済み config に混ざる source_code サブフィールドは再導入しない。
    """
    from src.services import report_duplicate

    embedded_config = {
        "input": "source",
        "question": "Source title",
        "intro": "Source description",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "extraction": {"prompt": "extract"},
        "hierarchical_overview": {"prompt": "overview"},
        "hierarchical_aggregation": {},
        "embedding": {"model": "text-embedding-3-large", "source_code": "some-normalized-code"},
    }

    config = report_duplicate._build_analysis_core_config_from_embedded_config(embedded_config)

    assert config["embedding"] == {"model": "text-embedding-3-large"}


# ---------------------------------------------------------------------------
# 再利用での複製後に、analysis-core が中間成果物を本当に再利用するか
# ---------------------------------------------------------------------------

SOURCE_SLUG = "source"
NEW_SLUG = "copy"
COMMENT_COUNT = 5


@pytest.fixture
def reuse_env(monkeypatch, tmp_path):
    """複製元の作成から複製後の実行計画までを、一時ディレクトリの中で通すための準備"""
    pytest.importorskip("analysis_core")
    from src.services import report_duplicate, report_launcher

    env = SimpleNamespace(
        reports=tmp_path / "reports",
        configs=tmp_path / "configs",
        inputs=tmp_path / "inputs",
        launched=[],
    )
    for module in (report_duplicate, report_launcher):
        monkeypatch.setattr(module.settings, "REPORT_DIR", env.reports)
        monkeypatch.setattr(module.settings, "CONFIG_DIR", env.configs)
        monkeypatch.setattr(module.settings, "INPUT_DIR", env.inputs)
    # リモートのストレージは使わず、analysis-core のサブプロセスも起動しない
    monkeypatch.setattr(report_duplicate, "ReportSyncService", MagicMock())
    monkeypatch.setattr(report_duplicate, "slug_exists", lambda slug: False)
    monkeypatch.setattr(report_duplicate, "add_new_report_to_status_from_config", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        report_duplicate,
        "launch_report_generation_from_config",
        lambda config_path, slug, user_api_key=None: env.launched.append(config_path),
    )
    return env


def _create_source_report(analysis_mode: str):
    """管理画面からの新規作成と同じく、API の書き出し処理で複製元の設定と入力 CSV を作る"""
    from src.schemas.admin_report import Comment, Prompt, ReportInput
    from src.services.report_launcher import save_config_file, save_input_file

    report_input = ReportInput(
        input=SOURCE_SLUG,
        question="Q",
        intro="I",
        cluster=[2, 4],
        model="gpt-4o-mini",
        workers=1,
        prompt=Prompt(extraction="ex", initial_labelling="il", merge_labelling="ml", overview="ov"),
        comments=[Comment(id=str(i), comment=f"comment {i}") for i in range(COMMENT_COUNT)],
        provider="openai",
        analysis_mode=analysis_mode,
    )
    save_input_file(report_input)
    return save_config_file(report_input)


def _run_analysis_core(env, config_path, only=None) -> None:
    """analysis-core の initialization / run_step / termination で複製元の status を書く

    LLM や埋め込みを呼ばないよう、各ステップの中身だけを成果物ファイルを書く処理に差し替える。
    """
    from analysis_core.core import get_specs, initialization, run_step, termination

    config = initialization(
        config_path,
        only=only,
        skip_interaction=True,
        without_html=True,
        validate_api_keys_early=False,
        output_base_dir=env.reports,
        input_base_dir=env.inputs,
    )
    output_dir = env.reports / config["output_dir"]

    def fake_step(spec):
        def run(_config):
            # 本物のステップと同じく、spec が宣言する成果物（filename と extra_files）をすべて書く
            for name in (spec["filename"], *spec.get("extra_files", [])):
                (output_dir / name).write_text(spec["step"], encoding="utf-8")

        return run

    for spec in get_specs():
        run_step(spec["step"], fake_step(spec), config, env.reports)
    termination(config, None, env.reports)


def _duplicate_with_reuse(env, overrides=None):
    """管理画面の「再利用」と同じ要求で複製し、analysis-core に渡す config のパスを返す"""
    from src.schemas.admin_report import ReportDuplicateOverrides, ReportDuplicateRequest, ReportDuplicateReuse
    from src.services import report_duplicate

    payload = ReportDuplicateRequest(
        new_slug=NEW_SLUG,
        overrides=ReportDuplicateOverrides(**overrides) if overrides else None,
        reuse=ReportDuplicateReuse(enabled=True),
    )
    report_duplicate.duplicate_report(SOURCE_SLUG, payload)
    return env.launched[-1]


def _plan(env, config_path) -> dict:
    """API が起動するコマンドに --dry-run を付けたときと同じく、書き込みなしで実行計画を出す"""
    from analysis_core.core import initialization

    config = initialization(
        config_path,
        skip_interaction=True,
        without_html=True,
        validate_api_keys_early=False,
        persist_status=False,
        output_base_dir=env.reports,
        input_base_dir=env.inputs,
    )
    return {step["step"]: step for step in config["plan"]}


@pytest.mark.parametrize("after_label_edit", [False, True], ids=["completed", "after-label-edit"])
@pytest.mark.parametrize(
    ("analysis_mode", "overrides", "expected_run"),
    [
        pytest.param("hierarchical", None, ["hierarchical_overview", "hierarchical_aggregation"], id="hierarchical"),
        pytest.param(
            "hierarchical",
            {"cluster": [3, 6]},
            [
                "hierarchical_clustering",
                "hierarchical_initial_labelling",
                "hierarchical_merge_labelling",
                "hierarchical_overview",
                "hierarchical_aggregation",
            ],
            id="hierarchical-cluster-changed",
        ),
        pytest.param("llm_grouping", None, ["hierarchical_overview", "hierarchical_aggregation"], id="llm_grouping"),
    ],
)
def test_duplicate_with_reuse_reruns_only_changed_steps(
    reuse_env, analysis_mode, overrides, expected_run, after_label_edit
):
    """再利用での複製では、変えていないステップの成果物を analysis-core がそのまま使う。

    複製は入力 CSV を新しい slug の名前でコピーするので、完了記録に残る入力名（複製元の slug）を
    読み替えないと、input が変わったとみなされて抽出から全段が再実行される。
    """
    source_config_path = _create_source_report(analysis_mode)
    _run_analysis_core(reuse_env, source_config_path)
    records = "completed_jobs"
    if after_label_edit:
        # 管理画面でラベルを直すと aggregation だけを再実行し、上流の記録は previously_completed_jobs に移る
        _run_analysis_core(reuse_env, source_config_path, only="hierarchical_aggregation")
        records = "previously_completed_jobs"
    status_path = reuse_env.reports / SOURCE_SLUG / "hierarchical_status.json"
    source_status = json.loads(status_path.read_text(encoding="utf-8"))
    source_extraction = next(job for job in source_status[records] if job["step"] == "extraction")
    assert source_extraction["global_params"]["input"] == SOURCE_SLUG

    new_config_path = _duplicate_with_reuse(reuse_env, overrides)

    plan = _plan(reuse_env, new_config_path)
    assert [step for step, decision in plan.items() if decision["run"]] == expected_run


def test_duplicate_with_reuse_reruns_extraction_when_input_is_rebuilt(reuse_env):
    """複製元の入力 CSV が無く arguments から入力を作り直した場合は、中身が違うので抽出からやり直す"""
    source_config_path = _create_source_report("hierarchical")
    _run_analysis_core(reuse_env, source_config_path)
    (reuse_env.inputs / f"{SOURCE_SLUG}.csv").unlink()
    # 件数を元のコメント数と同じにし、extraction.limit の違いでは再実行にならないようにする
    arguments = [{"arg_id": f"A{i}_0", "argument": f"argument {i}"} for i in range(COMMENT_COUNT)]
    (reuse_env.reports / SOURCE_SLUG / "hierarchical_result.json").write_text(
        json.dumps({"arguments": arguments}), encoding="utf-8"
    )

    new_config_path = _duplicate_with_reuse(reuse_env)

    plan = _plan(reuse_env, new_config_path)
    assert plan["extraction"]["run"] is True
    assert plan["extraction"]["reason"] == "some parameters changed: input"
