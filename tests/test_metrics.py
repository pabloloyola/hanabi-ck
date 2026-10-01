from hanabi_ck.metrics import aggregate_games


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
