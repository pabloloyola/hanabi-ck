from hanabi_ck.metrics import aggregate_games, summarize_game


def _game(score: int, *, valid: bool) -> dict:
    return {
        "valid": valid,
        "score": score,
        "perfect": False,
        "failed": False,
        "turns": 10,
        "plays": score,
        "successful_plays": score,
        "misplays": 0,
        "epistemically_safe_plays": score,
        "epistemically_unsafe_plays": 0,
        "successful_unsafe_plays": 0,
        "unsafe_play_rate": 0.0,
        "discards": 2,
        "hints": 3,
        "fallback_count": 0,
        "fallback_rate": 0.0,
        "successful_plays_per_hint": score / 3,
        "agent_error_count": 0 if valid else 1,
    }


def test_aggregate_excludes_aborted_games_from_performance():
    result = aggregate_games([
        _game(12, valid=True),
        _game(99, valid=False),
    ])

    assert result["n_games"] == 2
    assert result["n_valid_games"] == 1
    assert result["n_aborted_games"] == 1
    assert result["agent_error_count"] == 1
    assert result["mean_score"] == 12


def test_summarize_distinguishes_physical_success_from_epistemic_safety():
    turns = [
        {
            "action": {"type": "play", "card_index": 0},
            "outcome": {"play_success": True},
            "epistemically_safe_play": False,
            "agent": {"fallback_used": False},
        },
        {
            "action": {"type": "play", "card_index": 1},
            "outcome": {"play_success": False},
            "epistemically_safe_play": False,
            "agent": {"fallback_used": False},
        },
    ]
    final_state = {"score": 1, "life_tokens": 2}

    result = summarize_game(turns, final_state)

    assert result["successful_plays"] == 1
    assert result["misplays"] == 1
    assert result["epistemically_unsafe_plays"] == 2
    assert result["successful_unsafe_plays"] == 1
    assert result["unsafe_play_rate"] == 1.0
