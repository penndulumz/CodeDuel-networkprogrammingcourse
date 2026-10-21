"""Connect Four sample heuristic bot (reference opponent, level 2).

Strategy, in priority order:
1. Win immediately if a column completes four in a row.
2. Block the opponent's immediate winning column.
3. Avoid columns that let the opponent win right on top of our stone.
4. Otherwise pick the column with the best simple positional score
   (centre columns first, then lines we are building).
"""

ROWS = 6
COLS = 7
CENTER_ORDER = [3, 2, 4, 1, 5, 0, 6]


def _drop_row(board, col):
    """Return the row a stone dropped in col would land on, or -1 if full."""
    for row in range(ROWS - 1, -1, -1):
        if board[row][col] == 0:
            return row
    return -1


def _wins(board, row, col, player):
    """True if player owning (row, col) has four in a row through that cell."""
    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        count = 1
        for sign in (1, -1):
            r, c = row + dr * sign, col + dc * sign
            while 0 <= r < ROWS and 0 <= c < COLS and board[r][c] == player:
                count += 1
                r += dr * sign
                c += dc * sign
        if count >= 4:
            return True
    return False


def _completes_four(board, col, player):
    """True if dropping player's stone in col wins the game."""
    row = _drop_row(board, col)
    if row < 0:
        return False
    board[row][col] = player
    result = _wins(board, row, col, player)
    board[row][col] = 0
    return result


def _line_score(board, row, col, player):
    """Count friendly neighbours along every line through (row, col)."""
    score = 0
    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        for sign in (1, -1):
            r, c = row + dr * sign, col + dc * sign
            while 0 <= r < ROWS and 0 <= c < COLS and board[r][c] == player:
                score += 1
                r += dr * sign
                c += dc * sign
    return score


def get_move(board, my_player, history):
    """Return the column index (0..6) to play."""
    opponent = 2 if my_player == 1 else 1
    playable = [c for c in CENTER_ORDER if board[0][c] == 0]

    for col in playable:
        if _completes_four(board, col, my_player):
            return col
    for col in playable:
        if _completes_four(board, col, opponent):
            return col

    best_col = playable[0]
    best_score = None
    for col in playable:
        row = _drop_row(board, col)
        board[row][col] = my_player
        # Would this stone give the opponent a winning cell directly above it?
        gives_away = row > 0 and _completes_four(board, col, opponent)
        board[row][col] = 0

        score = _line_score(board, row, col, my_player) * 2 + _line_score(board, row, col, opponent)
        score -= abs(3 - col)
        if gives_away:
            score -= 100
        if best_score is None or score > best_score:
            best_col, best_score = col, score
    return best_col
