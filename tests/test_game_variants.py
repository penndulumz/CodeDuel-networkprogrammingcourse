"""Unit tests for engine rule variants and inverted combat cycle."""

import pytest
from engine.game import (
    Game,
    GameState,
    beats,
    is_valid_move,
    make_move,
    generate_legal_moves,
    RULE_VARIANT_STANDARD,
    RULE_VARIANT_INVERTED_RPS,
    RULE_VARIANT_CUSTOM,
    SUPPORTED_RULE_VARIANTS,
)


def test_constants_defined():
    """Verify supported rule variant constants are correctly exposed."""
    assert RULE_VARIANT_STANDARD == "standard"
    assert RULE_VARIANT_INVERTED_RPS == "inverted_rps"
    assert RULE_VARIANT_CUSTOM == "custom"
    assert RULE_VARIANT_STANDARD in SUPPORTED_RULE_VARIANTS
    assert RULE_VARIANT_INVERTED_RPS in SUPPORTED_RULE_VARIANTS
    assert RULE_VARIANT_CUSTOM in SUPPORTED_RULE_VARIANTS
    assert len(SUPPORTED_RULE_VARIANTS) == 3


def test_custom_variant_uses_source_configured_cycle():
    """Custom combat follows the editable mapping without changing existing variants."""
    assert beats("R", "S", variant=RULE_VARIANT_CUSTOM) is True
    assert beats("S", "R", variant=RULE_VARIANT_CUSTOM) is False
    assert beats("R", "S", variant=RULE_VARIANT_STANDARD) is True
    assert beats("S", "R", variant=RULE_VARIANT_INVERTED_RPS) is True
    assert Game(variant=RULE_VARIANT_CUSTOM).variant == RULE_VARIANT_CUSTOM


def test_invalid_custom_rules_fail_only_custom_variant(monkeypatch):
    """A broken custom mapping raises only when custom rules are selected."""
    import engine.game as game_module

    monkeypatch.setitem(game_module.CUSTOM_RULES, "wins_over", {("R", "R")})
    assert beats("R", "S", variant=RULE_VARIANT_STANDARD) is True
    assert beats("S", "R", variant=RULE_VARIANT_INVERTED_RPS) is True
    with pytest.raises(ValueError, match="custom"):
        Game(variant=RULE_VARIANT_CUSTOM)


def test_custom_configuration_controls_board_setup_and_moves(monkeypatch):
    """Custom settings can define a smaller board, piece positions, and legal moves."""
    import engine.game as game_module

    monkeypatch.setattr(game_module, "CUSTOM_RULES", {
        "board_size": (4, 5),
        "starting_pieces": [(1, "R", 0, 0), (1, "P", 0, 1), (2, "S", 3, 4)],
        "moves": [(0, 1), (0, -1)],
        "wins_over": {("R", "S"), ("S", "P"), ("P", "R")},
        "goals": {1: (3, 4), 2: (0, 0)},
        "win_conditions": {"reach_goal": True, "wipeout": True},
    })

    game = Game(variant=RULE_VARIANT_CUSTOM)
    assert len(game.board) == 4
    assert len(game.board[0]) == 5
    assert game.board[0][0] == {"type": "R", "player": 1}
    assert game.board[3][4] == {"type": "S", "player": 2}
    assert game.get_valid_destinations(0, 0) == []
    game.board[0][1] = None
    assert game.get_valid_destinations(0, 0) == [(0, 1)]


def test_coordinate_helpers_support_custom_board_dimensions():
    """Custom boards can use dimensions beyond the original nine files and ranks."""
    from engine.game import coord_name, parse_coord

    assert coord_name(9, 26, board_size=(10, 27)) == "aa10"
    assert parse_coord("aa10", board_size=(10, 27)) == (9, 26)


def test_beats_standard_vs_inverted():
    """Verify combat outcomes under standard and inverted RPS variants."""
    # Standard: Rock beats Scissors, Scissors beats Paper, Paper beats Rock
    assert beats("R", "S", variant=RULE_VARIANT_STANDARD) is True
    assert beats("S", "P", variant=RULE_VARIANT_STANDARD) is True
    assert beats("P", "R", variant=RULE_VARIANT_STANDARD) is True

    # Standard non-winning
    assert beats("S", "R", variant=RULE_VARIANT_STANDARD) is False
    assert beats("P", "S", variant=RULE_VARIANT_STANDARD) is False
    assert beats("R", "P", variant=RULE_VARIANT_STANDARD) is False
    assert beats("R", "R", variant=RULE_VARIANT_STANDARD) is False
    assert beats("P", "P", variant=RULE_VARIANT_STANDARD) is False
    assert beats("S", "S", variant=RULE_VARIANT_STANDARD) is False

    # Default parameter must be standard
    assert beats("R", "S") is True
    assert beats("S", "R") is False

    # Inverted: Scissors beats Rock, Rock beats Paper, Paper beats Scissors
    assert beats("S", "R", variant=RULE_VARIANT_INVERTED_RPS) is True
    assert beats("R", "P", variant=RULE_VARIANT_INVERTED_RPS) is True
    assert beats("P", "S", variant=RULE_VARIANT_INVERTED_RPS) is True

    # Inverted non-winning
    assert beats("R", "S", variant=RULE_VARIANT_INVERTED_RPS) is False
    assert beats("P", "R", variant=RULE_VARIANT_INVERTED_RPS) is False
    assert beats("S", "P", variant=RULE_VARIANT_INVERTED_RPS) is False
    assert beats("R", "R", variant=RULE_VARIANT_INVERTED_RPS) is False
    assert beats("P", "P", variant=RULE_VARIANT_INVERTED_RPS) is False
    assert beats("S", "S", variant=RULE_VARIANT_INVERTED_RPS) is False

    # Unknown variant falls back to standard
    assert beats("R", "S", variant="unsupported_variant") is True
    assert beats("S", "R", variant="unsupported_variant") is False


def test_is_valid_move_combat_inverted():
    """Verify is_valid_move enforces inverted combat hierarchy."""
    # Setup empty board
    board = [[None for _ in range(9)] for _ in range(9)]
    # Place P1 Scissors at (4, 4)
    board[4][4] = {"type": "S", "player": 1}
    # Place P2 Rock at (4, 5)
    board[4][5] = {"type": "R", "player": 2}
    # Place P1 Rock at (2, 2)
    board[2][2] = {"type": "R", "player": 1}
    # Place P2 Scissors at (2, 3)
    board[2][3] = {"type": "S", "player": 2}

    move_scissors_takes_rock = ((4, 4), (4, 5))
    move_rock_takes_scissors = ((2, 2), (2, 3))

    # Under standard rules:
    # Rock takes Scissors is valid, Scissors takes Rock is invalid
    assert is_valid_move(board, move_rock_takes_scissors, 1, variant=RULE_VARIANT_STANDARD) is True
    assert is_valid_move(board, move_scissors_takes_rock, 1, variant=RULE_VARIANT_STANDARD) is False

    # Default variant must match standard
    assert is_valid_move(board, move_rock_takes_scissors, 1) is True
    assert is_valid_move(board, move_scissors_takes_rock, 1) is False

    # Under inverted rules:
    # Scissors takes Rock is valid, Rock takes Scissors is invalid
    assert is_valid_move(board, move_scissors_takes_rock, 1, variant=RULE_VARIANT_INVERTED_RPS) is True
    assert is_valid_move(board, move_rock_takes_scissors, 1, variant=RULE_VARIANT_INVERTED_RPS) is False


def test_is_valid_move_non_combat_and_invalid_formats():
    """Verify is_valid_move handles normal steps, empty squares, and format variants."""
    board = [[None for _ in range(9)] for _ in range(9)]
    board[4][4] = {"type": "P", "player": 1}

    # Moving to empty square is valid in both variants
    empty_move = ((4, 4), (4, 5))
    assert is_valid_move(board, empty_move, 1, variant=RULE_VARIANT_STANDARD) is True
    assert is_valid_move(board, empty_move, 1, variant=RULE_VARIANT_INVERTED_RPS) is True

    # Dict format support
    dict_move = {"from": (4, 4), "to": (4, 5)}
    assert is_valid_move(board, dict_move, 1, variant=RULE_VARIANT_INVERTED_RPS) is True

    # Wrong player
    assert is_valid_move(board, empty_move, 2, variant=RULE_VARIANT_INVERTED_RPS) is False

    # Out of bounds
    assert is_valid_move(board, ((4, 4), (4, 9)), 1, variant=RULE_VARIANT_INVERTED_RPS) is False

    # Jump distance > 1
    assert is_valid_move(board, ((4, 4), (6, 4)), 1, variant=RULE_VARIANT_INVERTED_RPS) is False


def test_make_move_combat_resolution_inverted():
    """Verify make_move executes inverted captures and rejects invalid combat."""
    board = [[None for _ in range(9)] for _ in range(9)]
    board[4][4] = {"type": "S", "player": 1}
    board[4][5] = {"type": "R", "player": 2}

    # Under inverted rules: P1 Scissors captures P2 Rock
    new_board, move_dict = make_move(
        board, ((4, 4), (4, 5)), player=1, variant=RULE_VARIANT_INVERTED_RPS
    )

    assert new_board[4][4] is None
    assert new_board[4][5] == {"type": "S", "player": 1}
    assert move_dict["player"] == 1
    assert move_dict["piece"] == "S"
    assert move_dict["captured"] == "R"
    assert move_dict["from"] == (4, 4)
    assert move_dict["to"] == (4, 5)
    assert "(" in move_dict["san"]  # Capture notation present

    # Original board should not be mutated
    assert board[4][4] == {"type": "S", "player": 1}
    assert board[4][5] == {"type": "R", "player": 2}

    # Attempting the same under standard rules must raise ValueError
    with pytest.raises(ValueError):
        make_move(board, ((4, 4), (4, 5)), player=1, variant=RULE_VARIANT_STANDARD)


def test_generate_legal_moves_respects_variant():
    """Verify generate_legal_moves enumerates captures matching active variant."""
    board = [[None for _ in range(9)] for _ in range(9)]
    # Place P1 Rock at (4, 4)
    board[4][4] = {"type": "R", "player": 1}
    # Place P2 Scissors at (3, 4)
    board[3][4] = {"type": "S", "player": 2}
    # Place P2 Paper at (5, 4)
    board[5][4] = {"type": "P", "player": 2}

    std_moves = generate_legal_moves(board, player=1, variant=RULE_VARIANT_STANDARD)
    inv_moves = generate_legal_moves(board, player=1, variant=RULE_VARIANT_INVERTED_RPS)

    # In standard: Rock takes Scissors ((4, 4), (3, 4)) is legal, Rock takes Paper is illegal
    assert ((4, 4), (3, 4)) in std_moves
    assert ((4, 4), (5, 4)) not in std_moves

    # In inverted: Rock takes Paper ((4, 4), (5, 4)) is legal, Rock takes Scissors is illegal
    assert ((4, 4), (5, 4)) in inv_moves
    assert ((4, 4), (3, 4)) not in inv_moves


def test_game_class_variant_lifecycle():
    """Verify Game and GameState lifecycle, cloning, and serialization with rule variants."""
    game = Game(variant=RULE_VARIANT_INVERTED_RPS)
    assert game.variant == RULE_VARIANT_INVERTED_RPS
    assert game.rule_variant == RULE_VARIANT_INVERTED_RPS

    # Verify GameState is compatible alias
    state = GameState(variant=RULE_VARIANT_INVERTED_RPS)
    assert state.variant == RULE_VARIANT_INVERTED_RPS
    assert isinstance(state, Game)

    # Fallback for unrecognized variant
    default_game = Game(variant="non_existent")
    assert default_game.variant == RULE_VARIANT_STANDARD
    assert default_game.rule_variant == RULE_VARIANT_STANDARD

    # Clone preservation
    cloned = game.clone()
    assert cloned.variant == RULE_VARIANT_INVERTED_RPS
    assert cloned.rule_variant == RULE_VARIANT_INVERTED_RPS

    # to_dict serialization includes rule_variant
    state_dict = game.to_dict()
    assert state_dict["rule_variant"] == RULE_VARIANT_INVERTED_RPS

    # export_history includes rule_variant
    exported = game.export_history()
    assert exported["rule_variant"] == RULE_VARIANT_INVERTED_RPS
    assert "history" in exported


def test_game_instance_moves_and_combat_inverted():
    """Verify Game methods get_valid_moves, is_valid_move, and apply_move under inverted rules."""
    board = [[None for _ in range(9)] for _ in range(9)]
    # P1 Scissors at (4, 4)
    board[4][4] = {"type": "S", "player": 1}
    # P2 Rock at (4, 5) and (8, 0)
    board[4][5] = {"type": "R", "player": 2}
    board[8][0] = {"type": "R", "player": 2}

    game = Game(board=board, turn=1, variant=RULE_VARIANT_INVERTED_RPS)

    # Scissors capturing Rock must be legal
    assert game.is_valid_move(((4, 4), (4, 5))) is True
    valid_moves = game.get_valid_moves()
    assert ((4, 4), (4, 5)) in valid_moves

    # Applying move succeeds and captures Rock
    res = game.apply_move((4, 4), (4, 5))
    assert res["ok"] is True
    assert res["captured"]["type"] == "R"
    assert game.board[4][5]["type"] == "S"
    assert game.turn == 2


def test_full_wipeout_under_inverted_rules():
    """Verify wipeout win condition works under inverted combat cycle."""
    board = [[None for _ in range(9)] for _ in range(9)]
    # Place P1 Scissors
    board[4][4] = {"type": "S", "player": 1}
    # Place only 1 remaining P2 Rock (others already absent)
    board[4][5] = {"type": "R", "player": 2}
    # Give P2 a Paper safely placed elsewhere
    board[8][8] = {"type": "P", "player": 2}

    game = Game(board=board, turn=1, variant=RULE_VARIANT_INVERTED_RPS)

    # P1 Scissors captures the last P2 Rock
    res = game.apply_move((4, 4), (4, 5))
    assert res["winner"] == 1
    assert res["win_reason"] == "wipeout"
    assert res["wiped_type"] == "R"
    assert game.is_game_over is True
