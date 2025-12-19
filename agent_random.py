# agent_random.py
import random

def get_move(board):
    # Takes the current board state and return a random legal move
    moves = list(board.legal_moves)
    return random.choice(moves)