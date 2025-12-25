import chess
import chess.svg
import chess.pgn
import agent_random
from agent_minimax import MinimaxAgent  # Import the new class

# Initialize the Minimax bot once.
# This runs __init__, loads the tables, and sets the depth.
minimax_bot = MinimaxAgent(depth=5)

# IMPORTANT: The TT persists across moves within a game for better performance.
# Only clear it at the start of a NEW GAME.

# agent dictionary
# We map the name to the specific function that calculates the move
# Note: minimax returns (move, score) tuple, random returns just move
AGENTS = {
    "random": agent_random.get_move,
    "minimax": minimax_bot.select_move  # Returns (move, score) tuple
}

def get_agent_setup():
    # 1. Create a list of the agent names so they have a specific order
    agent_names = list(AGENTS.keys())

    print("\nSelect your opponent:")
    for i, name in enumerate(agent_names):
        print(f"{i + 1}. {name}")

    while True:
        try:
            choice = int(input("Enter the number of the bot: "))

            # Check if the number is valid (between 1 and the length of the AGENTS list)
            if 1 <= choice <= len(agent_names):
                # Subtract 1 to convert back to the list's 0-indexing
                selected_name = agent_names[choice - 1]

                # Return both the function and the name (to handle different return types)
                return AGENTS[selected_name], selected_name
            else:
                print("Invalid number. Please choose from the list.")
        except ValueError:
            print("Please enter a valid number.")

def get_player_color():
    while True:
        choice = input("\nChoose your color (w/b): ").lower()
        if choice in ['w', 'white']:
            return chess.WHITE
        elif choice in ['b', 'black']:
            return chess.BLACK
        print("Invalid input. Please type 'w' or 'b'.")

def load_from_pgn():
    """Load a game position from PGN notation"""
    print("\n=== Load from PGN ===")
    print("Paste your PGN (can be multiple lines, end with an empty line):")

    pgn_lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        pgn_lines.append(line)

    pgn_string = " ".join(pgn_lines)

    # Parse the PGN
    try:
        from io import StringIO
        pgn_io = StringIO(pgn_string)
        game = chess.pgn.read_game(pgn_io)

        if game is None:
            # No headers, just moves - create a simple game
            board = chess.Board()
            # Try to parse as just move text
            moves = pgn_string.replace(".", " ").split()
            for move_text in moves:
                move_text = move_text.strip()
                if not move_text or move_text.isdigit():
                    continue
                try:
                    board.push_san(move_text)
                except:
                    continue
            return board
        else:
            # Proper PGN with headers
            board = game.board()
            for move in game.mainline_moves():
                board.push(move)
            return board
    except Exception as e:
        print(f"Error parsing PGN: {e}")
        print("Starting from initial position instead.")
        return chess.Board()

def start_game():
    # Clear TT/killers/history at the start of a NEW GAME
    # (but NOT between moves - that would lose major benefits)
    minimax_bot.clear_tt()

    # 1. Setup
    agent_move_function, agent_name = get_agent_setup()
    player_color = get_player_color()

    # Ask if user wants to load from PGN
    load_pgn = input("\nLoad from PGN? (y/n): ").lower()
    if load_pgn in ['y', 'yes']:
        board = load_from_pgn()
        print(f"\nLoaded position. {len(board.move_stack)} moves played.")
    else:
        # Initialize the Board (The Environment)
        # This creates a standard game starting at the initial position
        board = chess.Board()

    # 2. The Game Loop
    # We keep the game running until someone wins or draws
    while not board.is_game_over():
        # Display the board state (Text based for now)
        print("\n" + str(board))

        # Check if it's the player's turn or the agent's turn
        # board.turn is True if it's White's turn, False if it's Black's

        if board.turn == player_color:
            # Player Turn
            move_input = input("\nYour move (or 'undo' to take back): ")

            if move_input.lower() in ['quit', 'exit']:
                break

            # Handle undo command
            if move_input.lower() in ['undo', 'back', 'u']:
                if len(board.move_stack) >= 2:
                    # Undo the last 2 moves (opponent's move and your move)
                    board.pop()
                    board.pop()
                    print("Undid last 2 moves (yours and opponent's).")
                elif len(board.move_stack) == 1:
                    # Only 1 move on the stack
                    board.pop()
                    print("Undid last move.")
                else:
                    print("No moves to undo!")
                continue

            try:
                board.push_san(move_input)
            except ValueError:
                print("Invalid move. Try again.")
                continue
        else:
            # Agent's Turn
            print("\nOpponent is thinking...")

            # Call function stored in 'agent_move_function' to get agent's move
            # Note: minimax returns (move, score), random returns just move
            result = agent_move_function(board, endgame_time_limit=5.0) if agent_name == "minimax" else agent_move_function(board)

            if agent_name == "minimax":
                move, score = result
                # Display move with score evaluation
                score_str = f"{score:+d}" if score is not None else "N/A"
                print(f"Opponent played: {board.san(move)} (Score: {score_str})")
            else:
                move = result
                print(f"Opponent played: {board.san(move)}")

            board.push(move)
        
    # Game Over
    print("\n" + str(board))
    print("Game Over!")
    print("Result: ", board.result())
    print("\n--- Game PGN ---")
    
    # 1. Create a PGN object
    pgn = chess.pgn.Game()
    
    # 2. Add headers
    pgn.headers["Event"] = "User vs Python Bot"
    pgn.headers["Site"] = "Localhost"
    pgn.headers["Date"] = "????.??.??"
    pgn.headers["Round"] = "1"
    pgn.headers["White"] = "User"
    pgn.headers["Black"] = f"Minimax (Depth {minimax_bot.depth})"
    pgn.headers["Result"] = board.result()
    
    # 3. Add all moves from the game history
    node = pgn
    for move in board.move_stack:
        node = node.add_variation(move)
    
    # 4. Print the clean string
    print(pgn)
    print("----------------\n")

if __name__ == "__main__":
    start_game()