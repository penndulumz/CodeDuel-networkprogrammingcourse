"""Connect Four bot template - the smallest working bot.

Board: 6 rows x 7 columns, board[row][col] is 0 (empty), 1 or 2.
Row 0 is the TOP row, row 5 is the bottom row. Stones fall down a column.

Your job: return the index (0..6) of the column you want to drop a stone into.
A column is playable while its top cell board[0][col] is still 0.

Test it offline:
    python starter_kit/local_arena.py starter_kit/connect4_template.py starter_kit/connect4_bot.py --game connect4
Grade it offline:
    python starter_kit/grade.py starter_kit/connect4_template.py --game connect4
"""

import random

ROWS = 6
COLS = 7


def get_move(board, my_player, history):
    """Return the column (int 0..6) to drop a stone into.

    Args:
        board: 6x7 list of lists with 0 (empty), 1 (Player 1) or 2 (Player 2).
        my_player: 1 or 2 - the stones you own.
        history: previous moves, e.g. [{'turn': 1, 'player': 1, 'move': 3, 'cell': [5, 3]}].
    """
    playable = [col for col in range(COLS) if board[0][col] == 0]

    # Simple idea to start with: prefer the centre column, it is part of the most lines.
    if 3 in playable:
        return 3
    return random.choice(playable)
