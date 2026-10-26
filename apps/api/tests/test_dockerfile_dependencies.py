import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

ANALYSIS_CORE_INSTALL_ARG = re.compile(
    r"set\s+--\s+(?P<quote>[\"']?)(?P<path>/packages/analysis-core)(?P<extras>\[[^\]\"'\s]+])?(?P=quote)"
)
SELF_REFERENCING_EXTRA = re.compile(r"kouchou-ai-analysis-core\[(?P<extras>[A-Za-z0-9_,.-]+)]")
REQUIREMENT_NAME = re.compile(r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)")


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _api_optional_dependencies() -> dict[str, list[str]]:
    with (REPO_ROOT / "apps/api/pyproject.toml").open("rb") as pyproject:
        return tomllib.load(pyproject)["project"]["optional-dependencies"]


def _locked_package_names(lock_file: str) -> set[str]:
    names = set()
    for line in (REPO_ROOT / "apps/api" / lock_file).read_text().splitlines():
        if "==" in line and not line.lstrip().startswith("#"):
            names.add(_normalize_name(line.split("==", 1)[0].strip()))
    return names


def _analysis_core_optional_dependencies() -> dict[str, list[str]]:
    with (REPO_ROOT / "packages/analysis-core/pyproject.toml").open("rb") as pyproject:
        return tomllib.load(pyproject)["project"]["optional-dependencies"]


def _extra_names(requirement: str) -> set[str]:
    match = SELF_REFERENCING_EXTRA.match(requirement)
    assert match is not None, f"Unexpected full extra dependency: {requirement}"
    return {extra.strip() for extra in match.group("extras").split(",")}


def test_analysis_core_full_extra_includes_pipeline_optional_dependencies():
    optional_dependencies = _analysis_core_optional_dependencies()

    full_extra_references = [
        dependency for dependency in optional_dependencies["full"] if dependency.startswith("kouchou-ai-analysis-core[")
    ]
    assert full_extra_references, "analysis-core full extra must reference its optional dependency groups"

    included_extras = set()
    for dependency in full_extra_references:
        included_extras.update(_extra_names(dependency))
    assert {"gemini", "embeddings", "clustering"} <= included_extras


def test_api_dockerfile_installs_analysis_core_with_full_extra():
    dockerfile = (REPO_ROOT / "apps/api/Dockerfile").read_text()

    match = ANALYSIS_CORE_INSTALL_ARG.search(dockerfile)
    assert match is not None, "API Dockerfile must install the local analysis-core package"

    extras = match.group("extras")
    assert extras is not None, "API Dockerfile must install analysis-core with required extras"
    assert "full" in {extra.strip() for extra in extras.strip("[]").split(",")}
    assert match.group("quote"), "The analysis-core extra spec must be quoted to avoid shell glob expansion"


def test_api_locks_include_youtube_plugin_dependencies():
    # Docker イメージは lock だけを入れる（pyproject の extra は見ない）ので、lock を作るときに
    # --extra youtube を忘れると YouTube プラグインが「google-api-python-client is required」で動かない。
    # プラグインのテストは googleapiclient を偽物に差し替えるため、テストでは気づけない。
    youtube_requirements = _api_optional_dependencies()["youtube"]
    required = {_normalize_name(REQUIREMENT_NAME.match(req).group("name")) for req in youtube_requirements}
    assert required, "youtube extra must list the plugin's dependencies"

    for lock_file in ("requirements.lock", "requirements-dev.lock"):
        missing = required - _locked_package_names(lock_file)
        assert not missing, (
            f"{lock_file} lacks {sorted(missing)}; regenerate it with `uv pip compile ... --extra youtube` "
            "(the command is in the lock header)"
        )
