"""Shared fixtures for analysis-core tests.

`analysis_core.services.llm` calls `load_dotenv()` at import time, so a developer's
real API key in a `.env` file can reach the tests. Unit tests must never talk to
an external service: block outbound connections, and fail the test even when the
code under test swallows the connection error.

E2E tests (`tests/e2e/`, marked `e2e`) call real APIs on purpose and are exempt.
"""

import ipaddress
import socket

import pytest

_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex


def _is_external(address) -> bool:
    if not isinstance(address, tuple):
        return False  # AF_UNIX etc.
    host = address[0]
    if host == "localhost":
        return False
    try:
        return not ipaddress.ip_address(host).is_loopback
    except ValueError:
        return True


@pytest.fixture(autouse=True)
def _no_external_network(request, monkeypatch):
    if request.node.get_closest_marker("e2e"):
        yield
        return

    attempts = []

    def guarded_connect(sock, address):
        if _is_external(address):
            attempts.append(address)
            raise ConnectionRefusedError(f"External network access is blocked in unit tests: {address}")
        return _original_connect(sock, address)

    def guarded_connect_ex(sock, address):
        if _is_external(address):
            attempts.append(address)
            raise ConnectionRefusedError(f"External network access is blocked in unit tests: {address}")
        return _original_connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    yield
    assert not attempts, f"Test attempted external network access (mock the LLM/HTTP call): {attempts}"
