"""Rock-Paper-Scissors Chess Game Logic Engine.

This module provides the complete game simulation for standard and custom RPS variants:
- Board coordinates: 9x9 matrix where row 0 = rank 1, row 8 = rank 9; col 0 = file a, col 8 = file i.
- Pieces: 'R' (Rock), 'P' (Paper), 'S' (Scissors).
- Combat rules: Rock beats Scissors, Scissors beats Paper, Paper beats Rock (Standard),
  or Scissors beats Rock, Rock beats Paper, Paper beats Scissors (Inverted).
- Movement rules: 1 square in any of the 8 directions (like a King in chess).
- Win conditions:
    1. Reaching the opponent's home goal square (P1 -> i9 (8,8); P2 -> a1 (0,0)).
    2. Wiping out all 3 pieces of any single opponent piece type.
    3. Reaching turn 100 tiebreaker (remaining pieces, then positional points).
"""

from __future__ import annotations

import copy
from typing import Any


# Coordinate and board definitions
FILES: list[str] = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]
RANKS: list[str] = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]

# Piece types and UI iconography
TYPES: list[str] = ["R", "P", "S"]
TYPE_NAMES: dict[str, str] = {
    "R": "Rock",
    "P": "Paper",
    "S": "Scissors",
}
TYPE_ICONS: dict[str, str] = {
    "R": "✊",
    "P": "✋",
    "S": "✌",
}

# Rule variants
RULE_VARIANT_STANDARD: str = "standard"
RULE_VARIANT_INVERTED_RPS: str = "inverted_rps"
RULE_VARIANT_CUSTOM: str = "custom"
SUPPORTED_RULE_VARIANTS: list[str] = [
    RULE_VARIANT_STANDARD,
    RULE_VARIANT_INVERTED_RPS,
    RULE_VARIANT_CUSTOM,
]

# Goal squares for each player: P1 targets (8, 8) [i9], P2 targets (0, 0) [a1]
GOALS: dict[int, tuple[int, int]] = {
    1: (8, 8),
    2: (0, 0),
}

# Maximum turns before turn-limit tiebreaker triggers
MAX_TURNS: int = 100

# 8 directions for king-like movement
DIRECTIONS: list[tuple[int, int]] = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
]

# Edit this single block to design the custom game. Coordinates are (row, column),
# starting at (0, 0) in the bottom-left. Each movement offset is one legal move;
# long offsets jump over intervening squares. Existing variants ignore this block.
CUSTOM_RULES: dict[str, Any] = {
    "board_size": (9, 9),  # (rows, columns)
    "starting_pieces": [  # (player, piece_type, row, column)
            (1, "R", 0, 0), (1, "R", 0, 1), (1, "R", 0, 2),
            (1, "P", 0, 3), (1, "P", 0, 4), (1, "P", 0, 5),
            (1, "S", 0, 6), (1, "S", 0, 7), (1, "S", 0, 8),
            (2, "S", 8, 0), (2, "S", 8, 1), (2, "S", 8, 2),
            (2, "P", 8, 3), (2, "P", 8, 4), (2, "P", 8, 5),
            (2, "R", 8, 6), (2, "R", 8, 7), (2, "R", 8, 8),
    ],
    "moves": DIRECTIONS.copy(),
    # "moves": {
    #     1: [(1, -1), (1, 0), (1, 1)],   # P1
    #     2: [(-1, -1), (-1, 0), (-1, 1)] # P2
    # },
    "wins_over": {("R", "S"), ("S", "P"), ("P", "R")},
    "goals": {1: (8, 8), 2: (0, 0)},
    "win_conditions": {"reach_goal": True, "wipeout": False},
}


def beats(a: str, b: str, variant: str = RULE_VARIANT_STANDARD) -> bool:
    """Check if piece type 'a' beats piece type 'b' according to the specified rule variant.

    Under standard RPS rules:
        - Rock beats Scissors
        - Scissors beats Paper
        - Paper beats Rock

    Under inverted_rps rules:
        - Scissors beats Rock
        - Rock beats Paper
        - Paper beats Scissors

    Under custom rules, CUSTOM_RULES['wins_over'] defines each winner/loser matchup.

    Args:
        a: Attacking piece type ('R', 'P', or 'S').
        b: Defending piece type ('R', 'P', or 'S').
        variant: Game rule variant identifier (default: "standard").

    Returns:
        True if 'a' beats 'b' under the given variant, False otherwise.
    """
    if variant == RULE_VARIANT_CUSTOM:
        _validate_custom_rules()
        return (a, b) in CUSTOM_RULES["wins_over"]
    if variant == RULE_VARIANT_INVERTED_RPS:
        return (
            (a == "S" and b == "R")
            or (a == "R" and b == "P")
            or (a == "P" and b == "S")
        )
    return (
        (a == "R" and b == "S")
        or (a == "S" and b == "P")
        or (a == "P" and b == "R")
    )


def _validate_custom_rules() -> None:
    """Validate the editable custom game definition only when custom is selected."""
    if not isinstance(CUSTOM_RULES, dict):
        raise ValueError("CUSTOM_RULES must be a dictionary.")

    board_size = CUSTOM_RULES.get("board_size")
    if (
        not isinstance(board_size, (tuple, list))
        or len(board_size) != 2
        or any(not isinstance(size, int) or isinstance(size, bool) or size < 1 for size in board_size)
    ):
        raise ValueError("Custom board_size must contain positive (rows, columns).")
    rows, cols = board_size

    moves = CUSTOM_RULES.get("moves")
    if isinstance(moves, dict):
        if set(moves) != {1, 2}:
            raise ValueError("Custom moves dictionary must define players 1 and 2.")
        move_lists = moves.values()
    else:
        # Backward compatibility: a single list means both players share moves.
        move_lists = (moves,)
    for player_moves in move_lists:
        if not isinstance(player_moves, (list, tuple)) or not player_moves:
            raise ValueError("Each custom player must have a non-empty list of moves.")
        for offset in player_moves:
            if (
                not isinstance(offset, (tuple, list))
                or len(offset) != 2
                or any(not isinstance(step, int) or isinstance(step, bool) for step in offset)
                or offset == (0, 0)
                or list(offset) == [0, 0]
            ):
                raise ValueError("Each custom move must be a non-zero integer offset pair.")

    starting_pieces = CUSTOM_RULES.get("starting_pieces")
    if not isinstance(starting_pieces, (list, tuple)) or not starting_pieces:
        raise ValueError("Custom starting_pieces must contain at least one piece.")
    occupied: set[tuple[int, int]] = set()
    players: set[int] = set()
    for piece in starting_pieces:
        if (
            not isinstance(piece, (tuple, list))
            or len(piece) != 4
            or not isinstance(piece[0], int)
            or isinstance(piece[0], bool)
            or piece[0] not in (1, 2)
            or piece[1] not in TYPES
            or not isinstance(piece[2], int)
            or not isinstance(piece[3], int)
            or not (0 <= piece[2] < rows and 0 <= piece[3] < cols)
        ):
            raise ValueError("Each custom starting piece must be (player, type, row, column) on the board.")
        position = (piece[2], piece[3])
        if position in occupied:
            raise ValueError("Custom starting pieces cannot share a square.")
        occupied.add(position)
        players.add(piece[0])
    if players != {1, 2}:
        raise ValueError("Custom starting_pieces must include both players.")

    goals = CUSTOM_RULES.get("goals")
    if not isinstance(goals, dict) or set(goals) != {1, 2}:
        raise ValueError("Custom goals must define one coordinate for each player (1 and 2).")
    for goal in goals.values():
        if (
            not isinstance(goal, (tuple, list))
            or len(goal) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) for value in goal)
            or not (0 <= goal[0] < rows and 0 <= goal[1] < cols)
        ):
            raise ValueError("Each custom goal must be a valid (row, column) on the board.")

    win_conditions = CUSTOM_RULES.get("win_conditions")
    if (
        not isinstance(win_conditions, dict)
        or set(win_conditions) != {"reach_goal", "wipeout"}
        or any(not isinstance(enabled, bool) for enabled in win_conditions.values())
    ):
        raise ValueError("Custom win_conditions must define boolean reach_goal and wipeout flags.")

    expected_matchups = {frozenset(pair) for pair in (("R", "P"), ("P", "S"), ("R", "S"))}
    wins_over = CUSTOM_RULES.get("wins_over")
    if not isinstance(wins_over, (set, frozenset)):
        raise ValueError("Custom wins_over must be a set of (winner, loser) pairs.")

    actual_matchups: set[frozenset[str]] = set()
    for pair in wins_over:
        if (
            not isinstance(pair, tuple)
            or len(pair) != 2
            or pair[0] not in TYPES
            or pair[1] not in TYPES
            or pair[0] == pair[1]
        ):
            raise ValueError("Each custom rule must be a valid (winner, loser) pair.")
        matchup = frozenset(pair)
        if matchup in actual_matchups:
            raise ValueError("Custom rules must define only one winner per matchup.")
        actual_matchups.add(matchup)

    if actual_matchups != expected_matchups:
        raise ValueError("Custom wins_over must define exactly one winner for every R/P/S matchup.")



def coord_name(
    row: int,
    col: int,
    board_size: tuple[int, int] = (9, 9),
) -> str:
    """Convert matrix coordinates (row, col) to standard algebraic square name (e.g., 'a1', 'i9').

    Args:
        row: Zero-based row index.
        col: Zero-based column index.

    Returns:
        Spreadsheet-style coordinate such as 'a1', 'i9', or 'aa10'.

    Raises:
        ValueError: If the coordinate is outside board_size.
    """
    rows, cols = board_size
    if not (0 <= row < rows and 0 <= col < cols):
        raise ValueError(f"Coordinate ({row}, {col}) is outside the {rows}x{cols} board.")
    file_name = ""
    remaining = col + 1
    while remaining > 0:
        digit = (remaining - 1) % 26
        file_name = chr(ord("a") + digit) + file_name
        remaining = (remaining - 1) // 26
    return f"{file_name}{row + 1}"


def parse_coord(
    name: str,
    board_size: tuple[int, int] = (9, 9),
) -> tuple[int, int]:
    """Parse algebraic notation (e.g. 'a1', 'i9', 'aa10') to matrix coordinates.

    Args:
        name: Coordinate string like 'a1'.

    Returns:
        Tuple of (row, col).

    Raises:
        ValueError: If coordinate format or board_size bounds are invalid.
    """
    normalized = name.lower()
    split_at = 0
    while split_at < len(normalized) and normalized[split_at].isalpha():
        split_at += 1
    file_name, rank_name = normalized[:split_at], normalized[split_at:]
    if not file_name or not rank_name.isdigit() or int(rank_name) < 1:
        raise ValueError(f"Invalid coordinate format '{name}'.")

    col = 0
    for char in file_name:
        if not ("a" <= char <= "z"):
            raise ValueError(f"Invalid file in coordinate '{name}'.")
        col = col * 26 + ord(char) - ord("a") + 1
    row = int(rank_name) - 1
    rows, cols = board_size
    col -= 1
    if not (0 <= row < rows and 0 <= col < cols):
        raise ValueError(f"Coordinate '{name}' is outside the {rows}x{cols} board.")
    return row, col


def notation(
    piece: dict[str, Any],
    fr: int,
    fc: int,
    tr: int,
    tc: int,
    captured: dict[str, Any] | None = None,
    board_size: tuple[int, int] = (9, 9),
) -> str:
    """Generate Short Algebraic Notation (SAN) for a move.

    Format:
        Non-capture: [Icon][from]-[to], e.g. '✋d1-d2'
        Capture:     [Icon][from]x[to]([CapturedIcon]), e.g. '✊a1xa2(✌)'

    Args:
        piece: Dict representing moving piece with 'type' key.
        fr: From row index.
        fc: From col index.
        tr: To row index.
        tc: To col index.
        captured: Optional dict representing captured piece with 'type' key.

    Returns:
        Formatted SAN notation string.
    """
    tag = TYPE_ICONS[piece["type"]]
    from_name = coord_name(fr, fc, board_size)
    to_name = coord_name(tr, tc, board_size)
    if captured:
        captured_tag = TYPE_ICONS[captured["type"]]
        return f"{tag}{from_name}x{to_name}({captured_tag})"
    return f"{tag}{from_name}-{to_name}"


def create_initial_board(
    variant: str = RULE_VARIANT_STANDARD,
) -> list[list[dict[str, Any] | None]]:
    """Construct the initial board for the selected ruleset.

    Returns:
        A rows-by-columns list containing piece dictionaries or None.
    """
    if variant == RULE_VARIANT_CUSTOM:
        _validate_custom_rules()
        rows, cols = CUSTOM_RULES["board_size"]
        board: list[list[dict[str, Any] | None]] = [[None for _ in range(cols)] for _ in range(rows)]
        for player, piece_type, row, col in CUSTOM_RULES["starting_pieces"]:
            board[row][col] = {"type": piece_type, "player": player}
        return board

    board: list[list[dict[str, Any] | None]] = [[None for _ in range(9)] for _ in range(9)]
    p1_row = ["R", "R", "R", "P", "P", "P", "S", "S", "S"]
    p2_row = ["S", "S", "S", "P", "P", "P", "R", "R", "R"]

    for col in range(9):
        board[0][col] = {"type": p1_row[col], "player": 1}
        board[8][col] = {"type": p2_row[col], "player": 2}

    return board


def _movement_offsets(variant: str, player: int | None = None) -> list[tuple[int, int]]:
    """Return legal destination offsets for the selected ruleset."""
    if variant == RULE_VARIANT_CUSTOM:
        _validate_custom_rules()
        configured_moves = CUSTOM_RULES["moves"]
        if isinstance(configured_moves, dict):
            if player in (1, 2):
                return [tuple(offset) for offset in configured_moves[player]]
            return list(dict.fromkeys(
                tuple(offset)
                for player_moves in configured_moves.values()
                for offset in player_moves
            ))
        return [tuple(offset) for offset in configured_moves]
    return DIRECTIONS


def _goal_positions(variant: str) -> dict[int, tuple[int, int]]:
    """Return goal squares for the selected ruleset."""
    if variant == RULE_VARIANT_CUSTOM:
        _validate_custom_rules()
        return {player: tuple(position) for player, position in CUSTOM_RULES["goals"].items()}
    return GOALS


def _win_condition_enabled(name: str, variant: str) -> bool:
    """Return whether an optional win condition is enabled for this ruleset."""
    if variant == RULE_VARIANT_CUSTOM:
        _validate_custom_rules()
        return CUSTOM_RULES["win_conditions"][name]
    return True


def get_goal_positions(variant: str = RULE_VARIANT_STANDARD) -> dict[int, tuple[int, int]]:
    """Return goal squares for replay metadata and game presentation."""
    return copy.deepcopy(_goal_positions(variant))


def _parse_move_positions(
    move: Any,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Extract origin and destination coordinate tuples from various move formats.

    Args:
        move: Move representation: ((fr, fc), (tr, tc)), dict with 'from'/'to' keys, or 4-tuple.

    Returns:
        Tuple of ((from_row, from_col), (to_row, to_col)) or None if malformed.
    """
    if isinstance(move, dict):
        fr_pos = move.get("from")
        to_pos = move.get("to")
        if (
            isinstance(fr_pos, (tuple, list))
            and len(fr_pos) == 2
            and isinstance(to_pos, (tuple, list))
            and len(to_pos) == 2
            and not isinstance(fr_pos[0], bool)
            and not isinstance(fr_pos[1], bool)
            and not isinstance(to_pos[0], bool)
            and not isinstance(to_pos[1], bool)
        ):
            return ((int(fr_pos[0]), int(fr_pos[1])), (int(to_pos[0]), int(to_pos[1])))
        return None

    if isinstance(move, (tuple, list)):
        if len(move) == 2:
            fr_pos, to_pos = move[0], move[1]
            if (
                isinstance(fr_pos, (tuple, list))
                and len(fr_pos) == 2
                and isinstance(to_pos, (tuple, list))
                and len(to_pos) == 2
                and not isinstance(fr_pos[0], bool)
                and not isinstance(fr_pos[1], bool)
                and not isinstance(to_pos[0], bool)
                and not isinstance(to_pos[1], bool)
            ):
                return ((int(fr_pos[0]), int(fr_pos[1])), (int(to_pos[0]), int(to_pos[1])))
        elif len(move) == 4:
            if not any(isinstance(v, bool) for v in move):
                return ((int(move[0]), int(move[1])), (int(move[2]), int(move[3])))

    return None


def is_valid_move(
    board: list[list[dict[str, Any] | None]],
    move: Any,
    player: int,
    variant: str = RULE_VARIANT_STANDARD,
) -> bool:
    """Validate whether a proposed move is legal under the specified rule variant.

    Args:
        Board matrix.
        move: Move representation ((fr, fc), (tr, tc)) or dict.
        player: Player number (1 or 2) making the move.
        variant: Game rule variant identifier (default: "standard").

    Returns:
        True if the move is strictly legal, False otherwise.
    """
    coords = _parse_move_positions(move)
    if coords is None:
        return False

    (fr, fc), (tr, tc) = coords
    rows = len(board)
    cols = len(board[0]) if rows else 0
    if any(len(row) != cols for row in board):
        return False
    if not (0 <= fr < rows and 0 <= fc < cols and 0 <= tr < rows and 0 <= tc < cols):
        return False

    piece = board[fr][fc]
    if piece is None or piece.get("player") != player:
        return False

    dr, dc = tr - fr, tc - fc
    if (dr, dc) not in _movement_offsets(variant, player):
        return False

    target = board[tr][tc]
    if target is None:
        return True

    if target.get("player") == player:
        return False

    return beats(piece["type"], target["type"], variant=variant)


def make_move(
    board: list[list[dict[str, Any] | None]],
    move: Any,
    player: int,
    variant: str = RULE_VARIANT_STANDARD,
) -> tuple[list[list[dict[str, Any] | None]], dict[str, Any]]:
    """Execute a move on a board matrix copy, validating rules under the specified variant.

    Args:
        Board matrix.
        move: Move representation ((fr, fc), (tr, tc)) or dict.
        player: Player number (1 or 2) making the move.
        variant: Game rule variant identifier (default: "standard").

    Returns:
        Tuple of (new_board, move_dict) containing updated board matrix and move metadata.

    Raises:
        ValueError: If the move violates game rules under the active variant.
    """
    if not is_valid_move(board, move, player, variant=variant):
        raise ValueError(
            f"Illegal move {move} for player {player} under variant '{variant}'."
        )

    coords = _parse_move_positions(move)
    assert coords is not None
    (fr, fc), (tr, tc) = coords

    new_board = copy.deepcopy(board)
    piece = copy.deepcopy(new_board[fr][fc])
    assert piece is not None
    captured = copy.deepcopy(new_board[tr][tc])

    new_board[tr][tc] = piece
    new_board[fr][fc] = None

    san = notation(piece, fr, fc, tr, tc, captured, (len(board), len(board[0])))
    move_dict: dict[str, Any] = {
        "player": player,
        "from": (fr, fc),
        "to": (tr, tc),
        "piece": piece["type"],
        "captured": captured["type"] if captured else None,
        "san": san,
    }

    return new_board, move_dict


def generate_legal_moves(
    board: list[list[dict[str, Any] | None]],
    player: int,
    variant: str = RULE_VARIANT_STANDARD,
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Generate all legal moves available for a player under the specified variant.

    Args:
        Board matrix.
        player: Player number (1 or 2).
        variant: Game rule variant identifier (default: "standard").

    Returns:
        List of ((from_row, from_col), (to_row, to_col)) coordinate tuples.
    """
    legal_moves: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for r in range(len(board)):
        for c in range(len(board[r])):
            piece = board[r][c]
            if piece and piece.get("player") == player:
                for dr, dc in _movement_offsets(variant, player):
                    nr, nc = r + dr, c + dc
                    candidate = ((r, c), (nr, nc))
                    if is_valid_move(board, candidate, player, variant=variant):
                        legal_moves.append(candidate)
    return legal_moves


class Game:
    """Represents a game state and evaluates moves under its selected ruleset."""

    def __init__(
        self,
        board: list[list[dict[str, Any] | None]] | None = None,
        turn: int = 1,
        move_no: int = 1,
        max_turns: int = MAX_TURNS,
        variant: str = RULE_VARIANT_STANDARD,
    ) -> None:
        """Initialize game state.

        Args:
            board: Optional board matrix. If None, the selected ruleset's setup is used.
            turn: Current player turn (1 or 2). Defaults to 1.
            move_no: Move sequence number (starts at 1). Defaults to 1.
            max_turns: Maximum number of moves before tiebreaker triggers. Defaults to 100.
            variant: Active rule variant identifier ('standard', 'inverted_rps', or 'custom').
        """
        resolved_variant = variant if variant in SUPPORTED_RULE_VARIANTS else RULE_VARIANT_STANDARD
        if resolved_variant == RULE_VARIANT_CUSTOM:
            _validate_custom_rules()
            expected_size = tuple(CUSTOM_RULES["board_size"])
            provided_size = (len(board), len(board[0]) if board else 0) if board is not None else expected_size
            if provided_size != expected_size:
                raise ValueError(
                    f"Custom board must match configured size {expected_size}; received {provided_size}."
                )

        if board is None:
            self.board = create_initial_board(variant=resolved_variant)
        else:
            self.board = copy.deepcopy(board)

        self.turn: int = turn
        self.move_no: int = move_no
        self.max_turns: int = max_turns

        self.variant: str = resolved_variant
        self.rule_variant: str = self.variant

        self.winner: int | None = None
        self.win_reason: str | None = None  # 'goal', 'wipeout', 'max_turns'
        self.wiped_type: str | None = None  # 'R', 'P', 'S' if win_reason == 'wipeout'
        self.tiebreak_scores: dict[str, Any] | None = None
        self.history: list[dict[str, Any]] = []

    @property
    def is_game_over(self) -> bool:
        """Check if the game has concluded."""
        return self.winner is not None or self.win_reason is not None

    def count_pieces(self, player: int, piece_type: str | None = None) -> int:
        """Count surviving pieces for a player, optionally filtered by type.

        Args:
            player: 1 or 2.
            piece_type: 'R', 'P', 'S', or None to count all pieces.

        Returns:
            Number of matching pieces remaining on the board.
        """
        count = 0
        for r in range(len(self.board)):
            for c in range(len(self.board[r])):
                cell = self.board[r][c]
                if cell and cell["player"] == player:
                    if piece_type is None or cell["type"] == piece_type:
                        count += 1
        return count

    def _calculate_tiebreak_scores(self) -> dict[str, Any]:
        """Score remaining pieces and their position for a turn-limit result."""
        rows = len(self.board)
        cols = len(self.board[0]) if rows else 0
        goals = _goal_positions(self.variant)
        center_rows = {(rows - 1) // 2, rows // 2}
        center_cols = {(cols - 1) // 2, cols // 2}
        position_points = {1: 0, 2: 0}

        for row, board_row in enumerate(self.board):
            for col, piece in enumerate(board_row):
                if piece is None:
                    continue
                goal_row, goal_col = goals[piece["player"]]
                row_progress = (rows - 1) - abs(row - goal_row)
                position_points[piece["player"]] += row_progress
                if row in center_rows and col in center_cols:
                    position_points[piece["player"]] += 2

        return {
            "remaining_pieces": {1: self.count_pieces(1), 2: self.count_pieces(2)},
            "position_points": position_points,
        }

    def get_valid_destinations(self, row: int, col: int) -> list[tuple[int, int]]:
        """Get all legal target coordinates for a piece located at (row, col).

        Args:
            row: Row index of piece.
            col: Col index of piece.

        Returns:
            List of valid (target_row, target_col) coordinates.
        """
        piece = self.board[row][col]
        if piece is None or piece["player"] != self.turn or self.is_game_over:
            return []

        valid: list[tuple[int, int]] = []
        rows = len(self.board)
        cols = len(self.board[0]) if rows else 0
        for dr, dc in _movement_offsets(self.variant, piece["player"]):
            nr, nc = row + dr, col + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                target = self.board[nr][nc]
                if target is None:
                    # Move to empty square
                    valid.append((nr, nc))
                elif target["player"] != piece["player"] and beats(
                    piece["type"], target["type"], variant=self.variant
                ):
                    # Capture opponent piece with winning RPS type
                    valid.append((nr, nc))
        return valid

    def get_valid_moves(
        self, player: int | None = None
    ) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        """Generate all legal moves available for the specified player.

        Args:
            player: Player number (1 or 2). Defaults to current turn if None.

        Returns:
            List of ((from_row, from_col), (to_row, to_col)) tuples.
        """
        if self.is_game_over:
            return []

        active_player = self.turn if player is None else player
        return generate_legal_moves(self.board, active_player, variant=self.variant)

    def is_valid_move(self, move: Any, player: int | None = None) -> bool:
        """Check if a move is valid under this game's active variant.

        Args:
            move: Move coordinates ((fr, fc), (tr, tc)) or dict.
            player: Player number (1 or 2). Defaults to current turn.

        Returns:
            True if legal, False otherwise.
        """
        if self.is_game_over:
            return False
        active_player = self.turn if player is None else player
        return is_valid_move(self.board, move, active_player, variant=self.variant)

    def generate_legal_moves(
        self, player: int | None = None
    ) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        """Generate all legal moves available under the active variant.

        Args:
            player: Player number (1 or 2). Defaults to current turn.

        Returns:
            List of ((from_row, from_col), (to_row, to_col)) tuples.
        """
        return self.get_valid_moves(player=player)

    def apply_move(
        self, from_pos: tuple[int, int], to_pos: tuple[int, int]
    ) -> dict[str, Any]:
        """Apply a move to the board, update state, check win conditions, and switch turn.

        Args:
            from_pos: (from_row, from_col) tuple.
            to_pos: (to_row, to_col) tuple.

        Returns:
            Dictionary containing move result details:
                - ok: bool
                - winner: int | None
                - win_reason: str | None ('goal', 'wipeout', 'max_turns')
                - wiped_type: str | None ('R', 'P', 'S')
                - captured: dict | None
                - san: str
                - from: tuple[int, int]
                - to: tuple[int, int]
                - piece: str
                - move_no: int

        Raises:
            ValueError: If game is already over or the move violates any game rules.
        """
        if self.is_game_over:
            raise ValueError("Cannot apply move: Game is already over.")

        fr, fc = from_pos
        tr, tc = to_pos

        rows = len(self.board)
        cols = len(self.board[0]) if rows else 0
        if not (0 <= fr < rows and 0 <= fc < cols and 0 <= tr < rows and 0 <= tc < cols):
            raise ValueError(f"Move coordinates out of bounds: {from_pos} -> {to_pos}")

        piece = self.board[fr][fc]
        if piece is None:
            raise ValueError(f"No piece found at {from_pos}.")
        if piece["player"] != self.turn:
            raise ValueError(
                f"Cannot move opponent piece at {from_pos}. Current turn is Player {self.turn}."
            )

        # Check the configured destination offset before resolving combat.
        dr, dc = tr - fr, tc - fc
        if (dr, dc) not in _movement_offsets(self.variant, piece["player"]):
            raise ValueError(f"Illegal move distance from {from_pos} to {to_pos}.")

        target = self.board[tr][tc]
        if target is not None:
            if target["player"] == piece["player"]:
                raise ValueError(f"Square {to_pos} is occupied by friendly piece.")
            if not beats(piece["type"], target["type"], variant=self.variant):
                raise ValueError(
                    f"Combat blocked: {piece['type']} does not beat {target['type']} at {to_pos} under variant '{self.variant}'."
                )

        # Move execution
        captured = self.board[tr][tc]
        self.board[tr][tc] = piece
        self.board[fr][fc] = None

        san = notation(
            piece,
            fr,
            fc,
            tr,
            tc,
            captured,
            (len(self.board), len(self.board[0])),
        )
        current_player = piece["player"]

        # Win Condition 1: Reaching opponent's home goal square
        goal = _goal_positions(self.variant)[current_player]
        if _win_condition_enabled("reach_goal", self.variant) and (tr, tc) == goal:
            self.winner = current_player
            self.win_reason = "goal"

        # Win Condition 2: Wiping out all pieces of any opponent type
        if (
            self.winner is None
            and captured is not None
            and _win_condition_enabled("wipeout", self.variant)
        ):
            opp_player = captured["player"]
            if self.count_pieces(opp_player, captured["type"]) == 0:
                self.winner = current_player
                self.win_reason = "wipeout"
                self.wiped_type = captured["type"]

        # Win Condition 3: Resolve the match at the turn limit using public score rules.
        if self.winner is None and self.move_no >= self.max_turns:
            self.win_reason = "max_turns"
            self.tiebreak_scores = self._calculate_tiebreak_scores()
            pieces = self.tiebreak_scores["remaining_pieces"]
            positions = self.tiebreak_scores["position_points"]
            if pieces[1] > pieces[2]:
                self.winner = 1
                self.tiebreak_scores["resolved_by"] = "remaining_pieces"
            elif pieces[2] > pieces[1]:
                self.winner = 2
                self.tiebreak_scores["resolved_by"] = "remaining_pieces"
            elif positions[1] > positions[2]:
                self.winner = 1
                self.tiebreak_scores["resolved_by"] = "position_points"
            elif positions[2] > positions[1]:
                self.winner = 2
                self.tiebreak_scores["resolved_by"] = "position_points"
            else:
                self.winner = None
                self.tiebreak_scores["resolved_by"] = "exact_tie"
            self.tiebreak_scores["winner"] = self.winner

        # Append move record to game history
        current_move_no = self.move_no
        move_record = {
            "turn": current_move_no,
            "player": current_player,
            "from": from_pos,
            "to": to_pos,
            "piece": piece["type"],
            "captured": captured["type"] if captured else None,
            "san": san,
        }
        self.history.append(move_record)

        # Increment move count and switch turn if match is still ongoing
        self.move_no += 1
        if not self.is_game_over:
            self.turn = 2 if self.turn == 1 else 1

        return {
            "ok": True,
            "winner": self.winner,
            "win_reason": self.win_reason,
            "wiped_type": self.wiped_type,
            "tiebreak_scores": copy.deepcopy(self.tiebreak_scores),
            "captured": captured,
            "san": san,
            "from": from_pos,
            "to": to_pos,
            "piece": piece["type"],
            "move_no": current_move_no,
        }

    def make_move(self, move: Any, player: int | None = None) -> dict[str, Any]:
        """Apply a move to this game state under the active variant.

        Args:
            move: Move coordinates ((fr, fc), (tr, tc)) or dict.
            player: Optional player making the move.

        Returns:
            Dictionary containing move result details.
        """
        coords = _parse_move_positions(move)
        if coords is None:
            raise ValueError(f"Invalid move format: {move}")
        from_pos, to_pos = coords
        if player is not None and player != self.turn:
            raise ValueError(
                f"Cannot move: Current turn is Player {self.turn}, not {player}."
            )
        return self.apply_move(from_pos, to_pos)

    def to_dict(self) -> dict[str, Any]:
        """Serialize complete game state into a dictionary.

        Returns:
            Dictionary representing current game snapshot.
        """
        return {
            "board": copy.deepcopy(self.board),
            "turn": self.turn,
            "move_no": self.move_no,
            "max_turns": self.max_turns,
            "board_size": (len(self.board), len(self.board[0]) if self.board else 0),
            "goals": copy.deepcopy(_goal_positions(self.variant)),
            "variant": self.variant,
            "rule_variant": self.variant,
            "winner": self.winner,
            "win_reason": self.win_reason,
            "wiped_type": self.wiped_type,
            "tiebreak_scores": copy.deepcopy(self.tiebreak_scores),
            "history": copy.deepcopy(self.history),
        }

    def export_history(self) -> dict[str, Any]:
        """Export serialized move history with rule variant metadata.

        Returns:
            Dictionary containing rule_variant, total_turns, and history move records.
        """
        return {
            "rule_variant": self.variant,
            "variant": self.variant,
            "total_turns": len(self.history),
            "history": copy.deepcopy(self.history),
        }

    def clone(self) -> Game:
        """Create an independent deep copy of the current game state.

        Returns:
            A cloned Game instance with isolated memory.
        """
        new_state = Game(
            board=self.board,
            turn=self.turn,
            move_no=self.move_no,
            max_turns=self.max_turns,
            variant=self.variant,
        )
        new_state.winner = self.winner
        new_state.win_reason = self.win_reason
        new_state.wiped_type = self.wiped_type
        new_state.tiebreak_scores = copy.deepcopy(self.tiebreak_scores)
        new_state.history = copy.deepcopy(self.history)
        return new_state


GameState = Game
