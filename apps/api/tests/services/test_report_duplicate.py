import json


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
    (report_dir / source_slug / "hierarchical_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "completed_jobs": [
                    {"step": "extraction"},
                    {"step": "embedding"},
                ],
                "previously_completed_jobs": [
                    {"step": "hierarchical_clustering"},
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
    assert not (new_output_dir / "hierarchical_result.json").exists()
    assert not (new_output_dir / "hierarchical_overview.txt").exists()

    assert status_calls == [(new_slug, written_config, source_slug)]
