import json

import httpx
import pytest

from hanabi_ck.agents import OpenAICompatibleAgent
from hanabi_ck.engine import HanabiGame


def run_responses(monkeypatch, statuses, *, retries=3, retry_after=None):
    requests, sleeps = [], []

    def handler(request):
        requests.append(json.loads(request.content))
        status = statuses.pop(0)
        content = (
            {"error": {"message": "upstream throttle", "metadata": {"provider": "Venice"}}}
            if status != 200
            else {
                "choices": [{"finish_reason": "stop", "message": {"content": '{"action_index":0}'}}]
            }
        )
        return httpx.Response(
            status, json=content, headers={"Retry-After": retry_after} if retry_after else {}
        )

    transport = httpx.MockTransport(handler)
    original = httpx.Client
    monkeypatch.setattr(
        "hanabi_ck.agents.httpx.Client", lambda **kw: original(transport=transport, **kw)
    )
    monkeypatch.setattr("hanabi_ck.agents.time.sleep", sleeps.append)
    agent = OpenAICompatibleAgent(
        name="test", model="model", api_key="test", http_max_retries=retries
    )
    game = HanabiGame(num_players=2, seed=0)
    decision = agent.act(game.observe(0), game.legal_actions(0), "test")
    return decision, requests, sleeps


def test_429_retries_identical_payload_and_records_error(monkeypatch):
    decision, requests, sleeps = run_responses(monkeypatch, [429, 429, 200])
    assert decision.parse_error is None
    assert len(requests) == 3 and requests[0] == requests[1] == requests[2]
    assert sleeps == [10, 20]
    assert [a["status_code"] for a in decision.http_attempts] == [429, 429, 200]
    assert decision.http_attempts[0]["response_body"]["error"]["message"] == "upstream throttle"


def test_retry_after_is_honored(monkeypatch):
    decision, _, sleeps = run_responses(monkeypatch, [503, 200], retry_after="7")
    assert decision.parse_error is None
    assert sleeps == [7]


def test_overlong_provider_delay_aborts_without_early_retry(monkeypatch):
    decision, requests, sleeps = run_responses(monkeypatch, [429], retry_after="120")
    assert "HTTPStatusError" in decision.parse_error
    assert len(requests) == 1 and not sleeps


def test_retry_exhaustion_preserves_provider_error(monkeypatch):
    decision, requests, sleeps = run_responses(monkeypatch, [429, 429, 429, 429])
    assert len(requests) == 4 and sleeps == [10, 20, 40]
    assert decision.action is None
    assert decision.api_response["error"]["message"] == "upstream throttle"


@pytest.mark.parametrize("status", [400, 401, 402, 403, 500])
def test_nonretryable_errors_are_not_retried(monkeypatch, status):
    decision, requests, sleeps = run_responses(monkeypatch, [status])
    assert len(requests) == 1 and not sleeps
    assert decision.parse_error


def test_default_keeps_single_request(monkeypatch):
    decision, requests, sleeps = run_responses(monkeypatch, [429], retries=0)
    assert len(requests) == 1 and not sleeps
    assert decision.http_attempts is None
