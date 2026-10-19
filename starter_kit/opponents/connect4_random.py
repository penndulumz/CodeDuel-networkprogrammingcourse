"""Connect Four reference opponent (level 1): drops into a random open column."""

import random


def get_move(board, my_player, history):
    """Return a random playable column."""
    return random.choice([col for col in range(len(board[0])) if board[0][col] == 0])
