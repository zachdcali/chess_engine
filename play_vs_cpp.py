#!/usr/bin/env python3
"""
Play against the C++ PestoPasta Engine in your terminal
Same interface as the Python version, but 100x faster!
"""

import chess
import chess.pgn
from cpp_engine_bridge import CppEngineAgent
from datetime import datetime

def print_board(board, user_is_white=True):
    """Print the board in a nice ASCII format."""
    print()
    board_str = str(board)
    # Replace piece characters with Unicode chess symbols
    # Standard convention: White = outlined (♔♕♖♗♘♙), Black = filled (♚♛♜♝♞♟)
    # python-chess uses: Uppercase = White, lowercase = black
    board_str = board_str.replace('R', '♖').replace('N', '♘').replace('B', '♗')
    board_str = board_str.replace('Q', '♕').replace('K', '♔').replace('P', '♙')
    board_str = board_str.replace('r', '♜').replace('n', '♞').replace('b', '♝')
    board_str = board_str.replace('q', '♛').replace('k', '♚').replace('p', '♟')

    # Flip board if user is playing as Black (show their pieces on bottom)
    # For White: Default orientation is correct (White on bottom, Black on top)
    # For Black: Rotate 180 degrees (reverse ranks AND files)
    if not user_is_white:
        lines = board_str.split('\n')
        lines = lines[::-1]  # Reverse the ranks (rows)
        # Also reverse each line to flip the files (columns)
        lines = [line[::-1] for line in lines]
        board_str = '\n'.join(lines)

    print(board_str)
    print()

def play_game():
    """Main game loop."""
    print("=" * 60)
    print("Welcome to PestoPasta C++ Engine!")
    print("=" * 60)
    print()
    print("Choose your side:")
    print("  1. Play as White")
    print("  2. Play as Black")

    while True:
        choice = input("\nYour choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Invalid choice! Please enter 1 or 2.")

    user_is_white = (choice == '1')

    print()
    print("Choose difficulty (engine search depth):")
    print("  6 - Easy (0.03s per move, ~1500 Elo)")
    print("  7 - Medium (0.13s per move, ~1700 Elo)")
    print("  8 - Hard (0.74s per move, ~1900 Elo)")
    print("  9 - Very Hard (3-5s per move, ~2100 Elo)")
    print("  10 - Expert (5-10s per move, ~2200+ Elo)")

    while True:
        depth_input = input("\nDepth (6-10, default 8): ").strip()
        if not depth_input:
            depth = 8
            break
        try:
            depth = int(depth_input)
            if 6 <= depth <= 10:
                break
            print("Please enter a number between 6 and 10.")
        except ValueError:
            print("Invalid input!")

    print(f"\n🤖 Initializing C++ engine (depth {depth})...")
    engine = CppEngineAgent(depth=depth)

    board = chess.Board()
    move_history = []

    # Setup PGN
    game = chess.pgn.Game()
    game.headers["Event"] = "User vs C++ Engine"
    game.headers["Site"] = "Localhost"
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = "1"
    game.headers["White"] = "User" if user_is_white else f"PestoPasta C++ (Depth {depth})"
    game.headers["Black"] = f"PestoPasta C++ (Depth {depth})" if user_is_white else "User"
    node = game

    print("\n" + "=" * 60)
    print("Game starting!")
    print("Commands: 'undo' to take back a move, 'quit' to exit")
    print("=" * 60)

    while not board.is_game_over():
        print_board(board, user_is_white)

        if (board.turn == chess.WHITE and user_is_white) or (board.turn == chess.BLACK and not user_is_white):
            # User's turn
            while True:
                move_str = input("Your move (or 'undo' to take back): ").strip()

                if move_str.lower() == 'quit':
                    print("\nGame aborted.")
                    return

                if move_str.lower() == 'undo':
                    if len(move_history) >= 2:
                        # Undo last 2 moves (user + engine)
                        board.pop()
                        board.pop()
                        move_history = move_history[:-2]
                        print("\n✓ Last two moves undone\n")
                        break
                    elif len(move_history) == 1:
                        # Only one move (user went first)
                        board.pop()
                        move_history = move_history[:-1]
                        print("\n✓ Last move undone\n")
                        break
                    else:
                        print("⚠️  Nothing to undo!")
                        continue

                try:
                    move = board.parse_san(move_str)
                    if move in board.legal_moves:
                        board.push(move)
                        move_history.append(move)
                        node = node.add_variation(move)
                        break
                    else:
                        print(f"⚠️  Illegal move: {move_str}")
                except ValueError:
                    # Try UCI format
                    try:
                        move = chess.Move.from_uci(move_str)
                        if move in board.legal_moves:
                            board.push(move)
                            move_history.append(move)
                            node = node.add_variation(move)
                            break
                        else:
                            print(f"⚠️  Illegal move: {move_str}")
                    except ValueError:
                        print(f"⚠️  Invalid move format: {move_str}")
                        print("    Use algebraic notation (e.g., e4, Nf3) or UCI (e.g., e2e4)")

        else:
            # Engine's turn
            print("Opponent is thinking...\n")

            move, score = engine.select_move(board)

            if move is None:
                print("❌ Engine failed to find a move!")
                break

            board.push(move)
            move_history.append(move)
            node = node.add_variation(move)

            # Show the move in SAN notation
            board.pop()
            move_san = board.san(move)
            board.push(move)

            score_str = f"{score:+d} cp" if score is not None else "N/A"
            print(f"Opponent played: {move_san} (eval: {score_str})\n")

    # Game over
    print_board(board, user_is_white)
    print("Game Over!")

    result = board.result()
    print(f"Result:  {result}")

    if board.is_checkmate():
        winner = "White" if board.turn == chess.BLACK else "Black"
        print(f"Checkmate! {winner} wins!")
    elif board.is_stalemate():
        print("Stalemate!")
    elif board.is_insufficient_material():
        print("Draw by insufficient material")
    elif board.can_claim_draw():
        print("Draw (repetition or 50-move rule)")

    # Set result
    game.headers["Result"] = result

    # Print PGN
    print("\n--- Game PGN ---")
    print(game)
    print("----------------\n")

    # Optionally save to file
    save = input("Save game to file? (y/n): ").strip().lower()
    if save == 'y':
        filename = f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pgn"
        with open(filename, 'w') as f:
            f.write(str(game))
        print(f"✓ Game saved to {filename}")

if __name__ == "__main__":
    try:
        play_game()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
