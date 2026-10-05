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


def test_ck1_is_asymmetric():
    p0 = get_condition("ck1_private").private_instruction(
        player_id=0, num_players=2, convention="SECRET CONVENTION"
    )
    p1 = get_condition("ck1_private").private_instruction(
        player_id=1, num_players=2, convention="SECRET CONVENTION"
    )
    assert "SECRET CONVENTION" in p0
    assert "SECRET CONVENTION" not in p1


def test_ck1_can_counterbalance_private_convention_to_player_1():
    condition = get_condition("ck1_private")

    p0 = condition.private_instruction(
        player_id=0,
        num_players=2,
        convention="PRIVATE_MARKER",
        informed_players={1},
    )
    p1 = condition.private_instruction(
        player_id=1,
        num_players=2,
        convention="PRIVATE_MARKER",
        informed_players={1},
    )

    assert "PRIVATE_MARKER" not in p0
    assert "PRIVATE_MARKER" in p1


def test_ck1_informed_local_wording_matches_ck2_shared():
    convention = "SAME C"
    ck1 = get_condition("ck1_private").private_instruction(
        player_id=1,
        num_players=2,
        convention=convention,
        informed_players={1},
    )
    ck2 = get_condition("ck2_shared").private_instruction(
        player_id=1,
        num_players=2,
        convention=convention,
    )

    assert ck1 == ck2



def test_minimal_pair_ck2_and_ck3_change_only_epistemic_status():
    convention = "TEST CONVENTION"
    ck2 = get_condition("ck2_shared").private_instruction(
        player_id=0,
        num_players=2,
        convention=convention,
        wording_variant="minimal_pair",
    )
    ck3 = get_condition("ck3_mutual").private_instruction(
        player_id=0,
        num_players=2,
        convention=convention,
        wording_variant="minimal_pair",
    )

    assert convention in ck2
    assert convention in ck3
    assert "do not establish whether any other player has it" in ck2
    assert "explicitly establish that every other player has" in ck3


def test_minimal_pair_keeps_ck1_informed_local_wording_equal_to_ck2():
    convention = "SAME C"
    ck1 = get_condition("ck1_private").private_instruction(
        player_id=1,
        num_players=2,
        convention=convention,
        informed_players={1},
        wording_variant="minimal_pair",
    )
    ck2 = get_condition("ck2_shared").private_instruction(
        player_id=1,
        num_players=2,
        convention=convention,
        wording_variant="minimal_pair",
    )

    assert ck1 == ck2
