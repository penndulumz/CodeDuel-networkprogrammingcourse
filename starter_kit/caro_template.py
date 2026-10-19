"""Caro (Gomoku) bot template - the smallest working bot.

Board: 15 x 15, board[row][col] is 0 (empty), 1 or 2.
Five (or more) of your stones in a straight line - horizontal, vertical or
diagonal - wins the game.

Your job: return (row, col) of an EMPTY cell to place your stone on.

Test it offline:
    python starter_kit/local_arena.py starter_kit/caro_template.py starter_kit/caro_bot.py --game caro
Grade it offline:
    python starter_kit/grade.py starter_kit/caro_template.py --game caro
"""

import random

SIZE = 15


def get_move(board, my_player, history):
    """Return (row, col) of the cell to place a stone on.

    Args:
        board: 15x15 list of lists with 0 (empty), 1 (Player 1) or 2 (Player 2).
        my_player: 1 or 2 - the stones you own.
        history: previous moves, e.g. [{'turn': 1, 'player': 1, 'move': [7, 7], 'cell': [7, 7]}].
    """
    # First move of the game: take the centre.
    if board[7][7] == 0:
        return (7, 7)

    # Simple idea to start with: play next to the last stone that was placed.
    if history:
        last_row, last_col = history[-1]["cell"]
        neighbours = [
            (last_row + dr, last_col + dc)
            for dr in (-1, 0, 1)
            for dc in (-1, 0, 1)
            if 0 <= last_row + dr < SIZE and 0 <= last_col + dc < SIZE
            and board[last_row + dr][last_col + dc] == 0
        ]
        if neighbours:
            return random.choice(neighbours)

    empty = [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == 0]
    return random.choice(empty)
