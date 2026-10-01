from hanabi_ck.actions import Action
from hanabi_ck.engine import Card, HanabiGame, standard_deck


def test_standard_deck_has_50_cards():
    assert len(standard_deck()) == 50


def test_initial_state_two_players():
    game = HanabiGame(num_players=2, seed=0)
    assert len(game.hands[0]) == 5
    assert len(game.hands[1]) == 5
    assert len(game.deck) == 40
    assert game.information_tokens == 8
    assert game.life_tokens == 3
    assert game.score == 0


def test_observation_hides_own_cards():
    game = HanabiGame(num_players=2, seed=0)
    obs = game.observe(0).to_dict()
    assert 0 not in obs["other_hands"]
    assert 1 in obs["other_hands"]
    assert len(obs["own_knowledge"]) == 5
    for k in obs["own_knowledge"]:
        assert len(k["possible_colors"]) == 5
        assert len(k["possible_ranks"]) == 5


def test_hint_updates_positive_and_negative_knowledge():
    game = HanabiGame(num_players=2, seed=3)
    target = 1
    rank = game.hands[target][0].rank
    action = Action.hint(target, "rank", rank)
    assert action in game.legal_actions(0)

    truth = [c.rank == rank for c in game.hands[target]]
    game.step(action)

    for matches, k in zip(truth, game.knowledge[target]):
        if matches:
            assert k.possible_ranks == {rank}
        else:
            assert rank not in k.possible_ranks


def test_discard_not_legal_at_eight_tokens():
    game = HanabiGame(num_players=2, seed=0)
    assert all(a.type != "discard" for a in game.legal_actions())


def test_play_advances_turn():
    game = HanabiGame(num_players=2, seed=0)
    game.step(Action.play(0))
    if not game.done:
        assert game.current_player == 1


def test_final_round_gives_every_player_one_more_turn_after_last_draw():
    game = HanabiGame(num_players=2, seed=0)
    game.deck = [Card("R", 1)]
    game.final_turns_remaining = None
    game.information_tokens = 7

    game.step(Action.discard(0))
    assert game.final_turns_remaining == 2
    assert not game.done

    game.step(Action.play(0))
    assert game.final_turns_remaining == 1
    assert not game.done

    game.step(Action.play(0))
    assert game.final_turns_remaining == 0
    assert game.done
