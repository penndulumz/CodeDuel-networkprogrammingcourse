"""Place-a-stone grid games: Connect Four and Caro (Gomoku).

Both games share the same shape, so they share one engine:
- The board is a rows x cols matrix of ints: 0 = empty, 1 = Player 1, 2 = Player 2.
- Players alternate placing one stone per turn; Player 1 always moves first.
- A player wins by forming an unbroken line of `win_length` stones horizontally,
  vertically, or diagonally. A full board without such a line is a draw.

The only difference is how a move is expressed:
- Connect Four uses gravity, so a move is a single column index (int). The stone
  falls to the lowest empty cell of that column.
- Caro lets a stone go anywhere, so a move is a (row, col) pair.

Bots receive exactly the same call signature as the RPS 9x9 game:
    get_move(board, my_player, history) -> move
so students learn one interface and can switch games freely.
"""

from __future__ import annotations

import copy
from typing import Any

# The four line directions that need checking (the other four are their mirrors).
LINE_DIRECTIONS: list[tuple[int, int]] = [(0, 1), (1, 0), (1, 1), (1, -1)]


class GridGame:
    """Shared rules engine for alternating stone-placement games.

    Subclasses set the board size, the line length needed to win, and whether
    stones fall with gravity (Connect Four) or are placed freely (Caro).
    """

    slug: str = "grid"
    rows: int = 3
    cols: int = 3
    win_length: int = 3
    gravity: bool = False

    def __init__(self) -> None:
        """Start a new game on an empty board with Player 1 to move."""
        self.board: list[list[int]] = [[0] * self.cols for _ in range(self.rows)]
        self.turn: int = 1
        self.history: list[dict[str, Any]] = []
        self.winner: int | None = None
        self.win_reason: str | None = None  # 'line' or 'board_full'
        self.winning_line: list[list[int]] = []

    # ------------------------------------------------------------------ state

    @property
    def is_game_over(self) -> bool:
        """True once a line has been formed or the board is full."""
        return self.win_reason is not None

    def initial_board(self) -> list[list[int]]:
        """Return an empty board of this game's size (used for replays)."""
        return [[0] * self.cols for _ in range(self.rows)]

    def clone(self) -> "GridGame":
        """Return an independent deep copy of this game."""
        return copy.deepcopy(self)

    # ------------------------------------------------------------------ moves

    def get_valid_moves(self, player: int | None = None) -> list[Any]:
        """List every legal move for the side to move.

        Args:
            player: Ignored except for symmetry with the RPS engine; only the
                side to move may place a stone.

        Returns:
            Column indices for gravity games, or (row, col) tuples otherwise.
        """
        if self.is_game_over:
            return []
        if self.gravity:
            return [c for c in range(self.cols) if self.board[0][c] == 0]
        return [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if self.board[r][c] == 0
        ]

    def normalize_move(self, raw_move: Any) -> Any | None:
        """Convert a bot's raw JSON move into this game's canonical move type.

        Booleans are rejected explicitly because bool is a subclass of int.

        Returns:
            An int column (gravity games), a (row, col) tuple, or None when
            the value is malformed.
        """
        if self.gravity:
            # Accept a bare column, or a one-element list like [3] for convenience.
            if isinstance(raw_move, (list, tuple)) and len(raw_move) == 1:
                raw_move = raw_move[0]
            if isinstance(raw_move, bool) or not isinstance(raw_move, int):
                return None
            return raw_move

        if not isinstance(raw_move, (list, tuple)) or len(raw_move) != 2:
            return None
        row, col = raw_move
        if isinstance(row, bool) or isinstance(col, bool):
            return None
        if not isinstance(row, int) or not isinstance(col, int):
            return None
        return (row, col)

    def landing_cell(self, move: Any) -> tuple[int, int]:
        """Return the board cell a legal move will occupy."""
        if not self.gravity:
            return move
        for row in range(self.rows - 1, -1, -1):
            if self.board[row][move] == 0:
                return (row, move)
        raise ValueError(f"Column {move} is full")

    def apply_move(self, move: Any) -> dict[str, Any]:
        """Place a stone for the side to move and update the result.

        Args:
            move: A canonical, legal move (see normalize_move/get_valid_moves).

        Returns:
            The history record appended for this move.

        Raises:
            ValueError: If the game is over or the move is illegal.
        """
        if self.is_game_over:
            raise ValueError("Game is already over")
        if move not in self.get_valid_moves():
            raise ValueError(f"Illegal move: {move}")

        player = self.turn
        row, col = self.landing_cell(move)
        self.board[row][col] = player

        record = {
            "turn": len(self.history) + 1,
            "player": player,
            "move": move if self.gravity else [row, col],
            "cell": [row, col],
        }
        self.history.append(record)

        line = self._line_through(row, col, player)
        if line:
            self.winner = player
            self.win_reason = "line"
            self.winning_line = [[r, c] for r, c in line]
        elif all(cell != 0 for row_cells in self.board for cell in row_cells):
            self.winner = None
            self.win_reason = "board_full"

        self.turn = 2 if player == 1 else 1
        return record

    def _line_through(self, row: int, col: int, player: int) -> list[tuple[int, int]]:
        """Return the winning line through (row, col) for player, or [] if none.

        Only the newly placed stone can complete a line, so checking the four
        directions through it is enough and keeps each move O(win_length).
        """
        for dr, dc in LINE_DIRECTIONS:
            cells = [(row, col)]
            for sign in (1, -1):
                r, c = row + dr * sign, col + dc * sign
                while 0 <= r < self.rows and 0 <= c < self.cols and self.board[r][c] == player:
                    cells.append((r, c))
                    r += dr * sign
                    c += dc * sign
            if len(cells) >= self.win_length:
                return sorted(cells)
        return []


class Connect4Game(GridGame):
    """Connect Four: 6 rows x 7 columns, stones fall down, connect 4 to win.

    Row 0 is the TOP of the board, row 5 is the bottom, matching how the board
    is printed and drawn.
    """

    slug = "connect4"
    rows = 6
    cols = 7
    win_length = 4
    gravity = True


class CaroGame(GridGame):
    """Caro (Gomoku): 15 x 15 board, place anywhere, 5 or more in a row wins."""

    slug = "caro"
    rows = 15
    cols = 15
    win_length = 5
    gravity = False
