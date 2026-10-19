"""Caro reference opponent (level 1): places next to existing stones at random."""

import random


def get_move(board, my_player, history):
    """Return a random empty cell adjacent to any stone (centre on move one)."""
    size = len(board)
    near = []
    for r in range(size):
        for c in range(size):
            if board[r][c] != 0:
                continue
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < size and 0 <= nc < size and board[nr][nc] != 0:
                        near.append((r, c))
                        break
                else:
                    continue
                break
    if not near:
        return (size // 2, size // 2)
    return random.choice(near)
