import importlib
import os
import subprocess
import sys

import pytest

from analysis_core.plugin import StepContext, StepInputs
from analysis_core.plugins.builtin.extraction import extraction_plugin
from analysis_core.services.timeouts import positive_timeout


@pytest.mark.parametrize("value", [0, -1, "", "abc", "1.5", 1.5, True])
def test_timeout_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        positive_timeout(value)


def test_environment_reaches_request_and_step_defaults():
    env = {**os.environ, "LLM_REQUEST_TIMEOUT_SECONDS": "617"}
    code = """
import inspect
from analysis_core.services import llm
from analysis_core.steps.extraction import EXTRACTION_WAIT_TIMEOUT_SECONDS
from analysis_core.steps.hierarchical_overview import OVERVIEW_TIMEOUT_SECONDS
assert EXTRACTION_WAIT_TIMEOUT_SECONDS == OVERVIEW_TIMEOUT_SECONDS == 617
for name in ("request_to_chat_ai", "request_to_openai", "request_to_azure_chatcompletion", "request_to_gemini_chatcompletion", "request_to_openrouter_chatcompletion", "request_to_local_llm"):
    assert inspect.signature(getattr(llm, name)).parameters["timeout_seconds"].default == 617
"""
    subprocess.run([sys.executable, "-c", code], env=env, check=True)


@pytest.mark.parametrize("override", [None, 919])
def test_workflow_extraction_passes_timeout_to_llm(tmp_path, monkeypatch, override):
    module = importlib.import_module("analysis_core.steps.extraction")
    from analysis_core.services.timeouts import DEFAULT_REQUEST_TIMEOUT_SECONDS

    output = tmp_path / "demo"
    output.mkdir()
    comments = tmp_path / "input.csv"
    comments.write_text("comment-id,comment-body\nc1,opinion\n")
    seen = []

    def request(**kwargs):
        seen.append(kwargs["timeout_seconds"])
        return '{"extractedOpinionList": ["opinion"]}', 2, 1, 3

    monkeypatch.setattr(module, "request_to_chat_ai", request)
    ctx = StepContext(output_dir=output, input_dir=tmp_path, dataset="demo", provider="local", model="m")
    extraction_plugin.run(
        ctx, StepInputs(artifacts={"comments": comments}), {"extraction": {"prompt": "p", "timeout_seconds": override}}
    )
    assert seen == [DEFAULT_REQUEST_TIMEOUT_SECONDS if override is None else override]
    assert (output / "args.csv").exists()
