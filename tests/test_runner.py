from hanabi_ck.agents import AgentDecision
from hanabi_ck.engine import HanabiGame
from hanabi_ck.runner import _resolve_agent_decision


def test_abort_policy_executes_no_action_after_agent_error():
    game = HanabiGame(num_players=2, seed=0)
    observation = game.observe(0)
    legal = game.legal_actions(0)
    decision = AgentDecision(
        action=None,
        parse_error="bad response",
    )

    action, fallback_used = _resolve_agent_decision(
        decision,
        error_policy="abort",
        observation=observation,
        legal_actions=legal,
    )

    assert action is None
    assert fallback_used is False


def test_safe_baseline_policy_uses_valid_fallback_action():
    game = HanabiGame(num_players=2, seed=0)
    observation = game.observe(0)
    legal = game.legal_actions(0)
    decision = AgentDecision(
        action=None,
        parse_error="bad response",
    )

    action, fallback_used = _resolve_agent_decision(
        decision,
        error_policy="safe_baseline",
        observation=observation,
        legal_actions=legal,
    )

    assert action in legal
    assert fallback_used is True
