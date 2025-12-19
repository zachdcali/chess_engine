import chess
import agent_random

# agent dictionary
AGENTS = {
    "random": agent_random.get_move
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

                # Return the actual function from the dictionary
                return AGENTS[selected_name]
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


def start_game():
    # 1. Setup
    agent_move_function = get_agent_setup()
    player_color = get_player_color()

    # 1. Initialize the Board (The Environment)
    # This creates a standard game starting at the inital position
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
            move_input = input("\nYour move: ")
            if move_input.lower() in ['quit', 'exit']:
                break
            try:
                board.push_san(move_input)
            except ValueError:
                print("Invalid move. Try again.")
                continue
        else:
            # Agent's Turn
            print("\nOpponent is thinking...")

            # Call function stored in 'agent_move_function' to get agent's move
            move = agent_move_function(board)

            print(f"Opponent played: {board.san(move)}")
            board.push(move)
        
    # Game Over
    print("\n" + str(board))
    print("Game Over!")
    print("Result: ", board.result())

if __name__ == "__main__":
    start_game()