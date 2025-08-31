import types
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))
from broadlistening.pipeline.services import llm


def test_system_role_removed(monkeypatch):
    dummy = types.SimpleNamespace(last=None)

    class DummyResponse:
        text = "ok"
        usage_metadata = types.SimpleNamespace(
            prompt_token_count=0, candidates_token_count=0, total_token_count=0
        )

    class DummyModel:
        def __init__(self, model, system_instruction=None):
            self.model = model
            self.system_instruction = system_instruction
            self.history = None

        def generate_content(self, history, generation_config=None):
            self.history = history
            return DummyResponse()

    def dummy_GenerativeModel(model, system_instruction=None):
        dummy.last = DummyModel(model, system_instruction)
        return dummy.last

    dummy_genai = types.SimpleNamespace(
        GenerativeModel=dummy_GenerativeModel,
        GenerationConfig=lambda **kwargs: kwargs,
        configure=lambda api_key: None,
    )

    dummy_exceptions = types.SimpleNamespace(
        ResourceExhausted=Exception,
        Unauthenticated=Exception,
        InvalidArgument=Exception,
    )

    monkeypatch.setattr(llm, "genai", dummy_genai)
    monkeypatch.setattr(llm, "google_exceptions", dummy_exceptions)

    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]

    text, in_tok, out_tok, total_tok = llm.request_to_gemini_chatcompletion(messages)

    assert dummy.last.system_instruction == "sys"
    assert all(m["role"] != "system" for m in dummy.last.history)
    assert text == "ok"
