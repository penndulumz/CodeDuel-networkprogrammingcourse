"""Caro (Gomoku) sample heuristic bot (reference opponent, level 2).

For every empty cell near existing stones, the bot measures how long a line it
would build (attack) and how long an opponent line it would break (defence),
counting open ends. It plays the cell with the highest combined score. This is
a classic, fast pattern-scoring approach - no search tree needed.
"""

SIZE = 15
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))

# Score for (stones in line including the new one, open ends).
PATTERN_SCORE = {
    (5, 0): 100000, (5, 1): 100000, (5, 2): 100000,
    (4, 2): 10000, (4, 1): 1000,
    (3, 2): 1000, (3, 1): 100,
    (2, 2): 100, (2, 1): 10,
    (1, 2): 10, (1, 1): 1,
}


def _evaluate(board, row, col, player):
    """Score placing player's stone on (row, col) across all four directions."""
    total = 0
    for dr, dc in DIRECTIONS:
        count = 1
        open_ends = 0
        for sign in (1, -1):
            r, c = row + dr * sign, col + dc * sign
            while 0 <= r < SIZE and 0 <= c < SIZE and board[r][c] == player:
                count += 1
                r += dr * sign
                c += dc * sign
            if 0 <= r < SIZE and 0 <= c < SIZE and board[r][c] == 0:
                open_ends += 1
        total += PATTERN_SCORE.get((min(count, 5), open_ends), 0)
    return total


def _candidates(board):
    """Empty cells within two steps of any stone (or the centre on move one)."""
    cells = set()
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] == 0:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < SIZE and 0 <= nc < SIZE and board[nr][nc] == 0:
                        cells.add((nr, nc))
    return sorted(cells) or [(7, 7)]


def get_move(board, my_player, history):
    """Return (row, col) with the best attack + defence score."""
    opponent = 2 if my_player == 1 else 1
    best_cell = None
    best_score = -1
    for row, col in _candidates(board):
        attack = _evaluate(board, row, col, my_player)
        defence = _evaluate(board, row, col, opponent)
        # Attack slightly outweighs defence so a winning move beats a block.
        score = attack * 1.1 + defence
        if score > best_score:
            best_cell, best_score = (row, col), score
    return best_cell
