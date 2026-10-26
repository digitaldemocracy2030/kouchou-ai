import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

ANALYSIS_CORE_INSTALL_ARG = re.compile(
    r"set\s+--\s+(?P<quote>[\"']?)(?P<path>/packages/analysis-core)(?P<extras>\[[^\]\"'\s]+])?(?P=quote)"
)
SELF_REFERENCING_EXTRA = re.compile(r"kouchou-ai-analysis-core\[(?P<extras>[A-Za-z0-9_,.-]+)]")


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
