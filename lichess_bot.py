import chess
import chess.pgn
import berserk
import time
import os
import threading
import random
import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from agent_minimax import MinimaxAgent

# ============================================================================
# LICHESS BOT - PestoPasta-Bot
# ============================================================================

# ============================================================================
# HEALTH CHECK SERVER (Required for Koyeb free tier)
# ============================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP server for cloud platform health checks"""

    def do_GET(self):
        """Respond to health check pings"""
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"PestoPasta-Bot is online and ready to play!")

    def log_message(self, format, *args):
        """Suppress HTTP server logs to keep console clean"""
        pass

def start_health_server():
    """Start health check server on port 8000 (Koyeb requirement)"""
    try:
        port = int(os.environ.get("PORT", 8000))
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        print(f"🏥 Health check server running on port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"⚠️  Health server error: {e}")

# Start health check server in background thread (daemon=True means it dies when main program exits)
health_thread = threading.Thread(target=start_health_server, daemon=True)
health_thread.start()

# ============================================================================
# LICHESS API SETUP
# ============================================================================

# Get Lichess API Token from environment variable (for security)
# For local testing, you can set: export LICHESS_TOKEN="your_token_here"
# For cloud deployment, set this in the platform's environment variables
LICHESS_TOKEN = os.environ.get("LICHESS_TOKEN")

if not LICHESS_TOKEN or LICHESS_TOKEN == "":
    print("❌ Error: LICHESS_TOKEN environment variable not set!")
    print("Set it with: export LICHESS_TOKEN='your_token_here'")
    exit(1)

# Initialize the Lichess client
session = berserk.TokenSession(LICHESS_TOKEN)
client = berserk.Client(session)

# Initialize the chess engine (depth 5 for standard search)
print("🤖 Initializing PestoPasta-Bot engine...")
engine = MinimaxAgent(depth=5)
print("✓ Engine ready!\n")

# Store game-specific information (game_id -> color mapping)
active_games = {}

def calculate_time_limit(wtime, btime, winc, binc, board):
    """
    Calculate the time limit for this move based on time control.

    Args:
        wtime: White's remaining time in milliseconds
        btime: Black's remaining time in milliseconds
        winc: White's increment in milliseconds
        binc: Black's increment in milliseconds
        board: Current board position

    Returns:
        float: Time limit in seconds for this move
    """
    # Determine which color we are and get our time/increment
    if board.turn == chess.WHITE:
        our_time = wtime / 1000.0  # Convert to seconds
        our_inc = winc / 1000.0
    else:
        our_time = btime / 1000.0
        our_inc = binc / 1000.0

    # Time management formula: divide remaining time over expected moves + use most of increment
    # Assume ~40 moves remaining in the game
    EXPECTED_MOVES = 40
    INCREMENT_USAGE = 0.8  # Use 80% of increment

    # Base time per move
    time_per_move = (our_time / EXPECTED_MOVES) + (our_inc * INCREMENT_USAGE)

    # Safety margin: never use more than 1/10 of remaining time on a single move
    max_time = our_time / 10.0

    # Ensure we have at least 0.1 seconds, but cap at max_time
    time_limit = max(0.1, min(time_per_move, max_time))

    # In very low time situations (< 10 seconds), be more conservative
    if our_time < 10:
        time_limit = min(time_limit, 0.5)

    return time_limit


def play_game(game_id):
    """
    Play a single game by streaming game state and making moves.

    Args:
        game_id: The Lichess game ID
    """
    print(f"\n{'='*60}")
    print(f"🎮 Starting game: {game_id}")
    print(f"{'='*60}\n")

    # Clear the transposition table for a new game
    print("🧹 Clearing transposition table for new game...")
    engine.clear_tt()

    # Stream the game state
    for event in client.bots.stream_game_state(game_id):
        # Handle different event types
        if event['type'] == 'gameFull':
            # Initial game state
            handle_game_state(game_id, event['state'], event)
        elif event['type'] == 'gameState':
            # Game state update (new move)
            handle_game_state(game_id, event)
        elif event['type'] == 'chatLine':
            # Chat message (ignore for now)
            pass


def handle_game_state(game_id, state, full_event=None):
    """
    Handle a game state update and make a move if it's our turn.

    Args:
        game_id: The Lichess game ID
        state: The game state dict
        full_event: The full event dict (only on first call with gameFull)
    """
    global active_games

    # Get the moves string and convert to a board position
    moves_str = state.get('moves', '')
    board = chess.Board()

    if moves_str:
        # Apply all moves to the board
        for move_uci in moves_str.split():
            board.push_uci(move_uci)

    # Determine our color (from full_event on first call, then from stored info)
    if full_event:
        # First time seeing this game - determine and store our color
        account_info = client.account.get()
        bot_username = account_info['username'].lower()

        white_player = full_event.get('white', {}).get('name', 'Unknown')
        black_player = full_event.get('black', {}).get('name', 'Unknown')
        print(f"⚔️  White: {white_player} vs Black: {black_player}")

        white_name = white_player.lower()
        black_name = black_player.lower()

        if bot_username == white_name:
            our_color = chess.WHITE
        elif bot_username == black_name:
            our_color = chess.BLACK
        else:
            print("⚠️  Could not determine bot color!")
            return

        # Store for future state updates
        active_games[game_id] = our_color
    else:
        # Retrieve our color from stored info
        our_color = active_games.get(game_id)
        if our_color is None:
            print("⚠️  Game color not found in active games!")
            return

    # Check if game is over
    if state['status'] != 'started':
        print(f"\n🏁 Game Over! Status: {state['status']}")
        # Clean up
        if game_id in active_games:
            del active_games[game_id]
        return

    # Check if it's our turn
    if board.turn != our_color:
        print("⏳ Waiting for opponent's move...")
        return

    # It's our turn! Calculate time limit
    wtime = state.get('wtime', 60000)
    btime = state.get('btime', 60000)
    winc = state.get('winc', 0)
    binc = state.get('binc', 0)

    time_limit = calculate_time_limit(wtime, btime, winc, binc, board)

    print(f"\n{'─'*60}")
    print(f"🧠 Bot's turn ({'White' if our_color == chess.WHITE else 'Black'})")
    print(f"⏱️  Time remaining: {wtime/1000:.1f}s (W) | {btime/1000:.1f}s (B)")
    print(f"⏱️  Time limit for this move: {time_limit:.2f}s")
    print(f"📊 Position: {len(board.move_stack)} moves played")
    print(f"{'─'*60}")

    # Calculate the move using our engine
    start_time = time.time()

    # Determine if we should use endgame time limit
    phase = engine.calculate_game_phase(board)
    if phase <= 12:  # Endgame
        # Use the calculated time limit for endgames
        move, score = engine.select_move(board, endgame_time_limit=time_limit)
    else:  # Middlegame/Opening
        # Fixed depth 5 in middlegame (fast)
        move, score = engine.select_move(board, endgame_time_limit=time_limit)

    elapsed = time.time() - start_time

    if move is None:
        print("❌ No legal moves available!")
        return

    # Display the move and evaluation
    move_san = board.san(move)
    score_str = f"{score:+d}" if score is not None else "N/A"

    print(f"\n✅ Decision: {move_san} | Evaluation: {score_str} cp")
    print(f"⏱️  Calculation time: {elapsed:.2f}s")
    print(f"{'─'*60}\n")

    # Make the move on Lichess
    try:
        client.bots.make_move(game_id, move.uci())
        print(f"📤 Move sent to Lichess: {move.uci()}")
    except Exception as e:
        print(f"❌ Error making move: {e}")


def accept_challenge(event):
    """
    Automatically accept incoming challenges.

    Args:
        event: The challenge event dict
    """
    challenge_id = event['challenge']['id']
    challenger = event['challenge']['challenger']['name']
    variant = event['challenge']['variant']['name']
    time_control = event['challenge'].get('timeControl', {})

    print(f"\n📨 Challenge received from {challenger}")
    print(f"   Variant: {variant}")
    print(f"   Time control: {time_control}")

    # Accept standard chess challenges only
    if variant == 'standard':
        try:
            client.bots.accept_challenge(challenge_id)
            print(f"✓ Challenge accepted!")
        except Exception as e:
            print(f"❌ Error accepting challenge: {e}")
    else:
        print(f"⚠️  Declined: Only standard chess is supported")
        try:
            client.bots.decline_challenge(challenge_id)
        except:
            pass


# ============================================================================
# HUNTER MODE - Actively seek out games with other bots
# ============================================================================

# Track currently playing games
currently_playing = set()

def is_bot_idle():
    """Check if bot is currently idle (not in any active games)"""
    try:
        # Get list of ongoing games
        ongoing = list(client.games.get_ongoing())
        return len(ongoing) == 0
    except:
        return False

def find_and_challenge_bot():
    """
    Find an online bot and challenge them to a game.

    IMPORTANT: Only challenges other BOTS, never humans (Lichess TOS requirement)
    """
    try:
        # Get list of online bots
        # Note: This uses the public API to find bots
        online_bots = list(client.users.get_live_streamers())

        # Filter for actual bots (have BOT title) and exclude ourselves
        account = client.account.get()
        our_username = account['username'].lower()

        # Get a list of top bots to challenge
        # We'll use the bot.get_online_bots() if available, otherwise fall back to searching
        try:
            # Get online bots from Lichess bot endpoint
            response = requests.get("https://lichess.org/api/bot/online", timeout=10)
            if response.status_code == 200:
                online_bots_list = []
                for line in response.text.strip().split('\n'):
                    if line:
                        bot_data = json.loads(line)
                        if bot_data.get('username', '').lower() != our_username:
                            online_bots_list.append(bot_data)

                if not online_bots_list:
                    print("💤 No online bots found to challenge")
                    return

                # Pick a random bot from the list
                target_bot = random.choice(online_bots_list)
                target_username = target_bot['username']

                print(f"\n🎯 Challenging bot: {target_username}")

                # Send challenge (3+2 Blitz, Rated)
                challenge_response = client.challenges.create(
                    target_username,
                    rated=True,  # Rated games to build rating
                    clock_limit=180,  # 3 minutes
                    clock_increment=2,  # 2 second increment
                    color='random',
                    variant='standard'
                )

                print(f"✓ Challenge sent to {target_username}!")

        except Exception as e:
            print(f"⚠️  Could not challenge bot: {e}")

    except Exception as e:
        print(f"⚠️  Error in hunter mode: {e}")

def hunter_loop():
    """
    Background thread that periodically challenges other bots when idle.

    Runs every 2 minutes to check if bot is idle and seeks new games.
    """
    print("🏹 Hunter mode activated - will seek games when idle")

    while True:
        try:
            # Wait 2 minutes between checks
            time.sleep(120)

            # Check if we're idle
            if is_bot_idle():
                print("\n💤 Bot is idle, looking for opponents...")
                find_and_challenge_bot()
            else:
                print("⚔️  Bot is currently playing")

        except Exception as e:
            print(f"⚠️  Hunter loop error: {e}")
            time.sleep(120)  # Wait before retrying

def start_hunter_mode():
    """Start the hunter mode in a background thread"""
    hunter_thread = threading.Thread(target=hunter_loop, daemon=True)
    hunter_thread.start()
    print("✓ Hunter mode started - bot will actively seek games\n")


def main():
    """
    Main bot loop: listen for events and handle challenges/games.
    """
    # Upgrade account to BOT status (only needs to be done once, but safe to call multiple times)
    try:
        print("🔧 Upgrading account to BOT status...")
        client.account.upgrade_to_bot()
        print("✓ Account is now a BOT!\n")
    except berserk.exceptions.ResponseError as e:
        if "already" in str(e).lower():
            print("✓ Account already has BOT status\n")
        else:
            print(f"⚠️  Error upgrading to BOT: {e}\n")

    # Get account info
    account = client.account.get()
    username = account['username']
    print(f"{'='*60}")
    print(f"🤖 PestoPasta-Bot ({username}) is now online!")
    print(f"{'='*60}")
    print(f"📡 Listening for challenges and games...")
    print(f"💡 Go to https://lichess.org/@/{username} to see your profile")
    print(f"{'='*60}\n")

    # Start hunter mode - actively seek games with other bots
    start_hunter_mode()

    # Stream incoming events (challenges and games)
    for event in client.bots.stream_incoming_events():
        if event['type'] == 'challenge':
            # New challenge received
            accept_challenge(event)
        elif event['type'] == 'gameStart':
            # Game is starting
            game_id = event['game']['id']
            print(f"\n🎮 Game starting: {game_id}")
            try:
                play_game(game_id)
            except Exception as e:
                print(f"❌ Error during game: {e}")
                import traceback
                traceback.print_exc()
        elif event['type'] == 'gameFinish':
            # Game finished
            game_id = event['game']['id']
            print(f"\n🏁 Game finished: {game_id}\n")
            print(f"{'='*60}")
            print(f"📡 Ready for next challenge...")
            print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Bot shutting down... Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
