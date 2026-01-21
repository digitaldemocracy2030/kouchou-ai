"""Pytest configuration for E2E tests.

E2E tests use real LLM API calls and are not run automatically.
They require OPENAI_API_KEY environment variable to be set.

Usage:
    # Run with API KEY
    OPENAI_API_KEY=sk-xxx pytest tests/e2e/ -v

    # Or use .env file
    # Create tests/e2e/.env with OPENAI_API_KEY=sk-xxx
    pytest tests/e2e/ -v
"""

import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "e2e: marks tests as end-to-end tests (require API KEY, not run automatically)",
    )


@pytest.fixture(scope="session")
def api_key():
    """Get OpenAI API key from environment.

    This fixture will skip all tests if the API key is not set,
    preventing accidental runs without proper authorization.
    """
    # Try to load from .env file in e2e directory
    e2e_env = Path(__file__).parent / ".env"
    if e2e_env.exists():
        load_dotenv(e2e_env)

    # Also try parent directories
    load_dotenv()

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        pytest.skip(
            "OPENAI_API_KEY not set - skipping E2E test. "
            "Set OPENAI_API_KEY environment variable or create tests/e2e/.env file."
        )
    return key


@pytest.fixture(scope="session")
def test_fixtures_dir():
    """Get the path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def small_comments_csv(test_fixtures_dir):
    """Get the path to small_comments.csv test fixture."""
    csv_path = test_fixtures_dir / "small_comments.csv"
    if not csv_path.exists():
        pytest.fail(f"Test fixture not found: {csv_path}")
    return csv_path


@pytest.fixture
def temp_dirs():
    """Create temporary directories for test inputs and outputs.

    Uses non-standard directory names to catch hardcoded path bugs.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        input_dir = base / "e2e_test_inputs"
        output_dir = base / "e2e_test_outputs"
        input_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
        yield {
            "base": base,
            "input_dir": input_dir,
            "output_dir": output_dir,
        }


@pytest.fixture
def pipeline_config(temp_dirs, api_key):
    """Create a minimal pipeline configuration for E2E testing.

    This configuration uses gpt-4o-mini for cost efficiency.
    """
    return {
        "input": "small_comments",
        "output_dir": "e2e_test_result",
        "question": "この意見の主なテーマは何ですか？",
        "intro": "E2Eテスト用のサンプル分析です。",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "_input_base_dir": str(temp_dirs["input_dir"]),
        "_output_base_dir": str(temp_dirs["output_dir"]),
        "is_pubcom": False,
        "is_embedded_at_local": False,
        "extraction": {
            "model": "gpt-4o-mini",
            "prompt": "以下のコメントから主要な意見や主張を抽出してください。",
            "workers": 1,
            "limit": 10,
            "properties": [],
            "categories": {},
        },
        "embedding": {
            "model": "text-embedding-3-small",
        },
        "hierarchical_clustering": {
            "cluster_nums": [2],  # Minimal clustering for test
        },
        "hierarchical_initial_labelling": {
            "model": "gpt-4o-mini",
        },
        "hierarchical_merge_labelling": {
            "model": "gpt-4o-mini",
        },
        "hierarchical_overview": {
            "model": "gpt-4o-mini",
        },
        "hierarchical_aggregation": {
            "hidden_properties": {},
        },
    }
