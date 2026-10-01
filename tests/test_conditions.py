from hanabi_ck.conditions import get_condition


def test_ck0_does_not_include_convention_text():
    text = get_condition("ck0").private_instruction(
        player_id=0, num_players=2, convention="SECRET CONVENTION"
    )
    assert "SECRET CONVENTION" not in text


def test_ck3_mentions_every_player_received_it():
    text = get_condition("ck3_mutual").private_instruction(
        player_id=0, num_players=2, convention="C"
    )
    assert "Every player was given this same convention" in text


def test_ck_inf_declares_common_knowledge():
    text = get_condition("ck_inf_common").private_instruction(
        player_id=0, num_players=2, convention="C"
    )
    assert "common knowledge" in text
