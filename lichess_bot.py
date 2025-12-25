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
        wtime: White's remaining time (milliseconds or timedelta)
        btime: Black's remaining time (milliseconds or timedelta)
        winc: White's increment (milliseconds or timedelta)
        binc: Black's increment (milliseconds or timedelta)
        board: Current board position

    Returns:
        float: Time limit in seconds for this move
    """
    # Convert all time values to seconds (handle both int/milliseconds and timedelta objects)
    def to_seconds(time_value):
        """Convert time value to seconds, handling both int and timedelta"""
        if time_value is None:
            return 0.0
        if hasattr(time_value, 'total_seconds'):
            # It's a timedelta object
            return time_value.total_seconds()
        else:
            # Assume it's milliseconds (int or float)
            return float(time_value) / 1000.0

    # Convert all inputs to seconds
    wtime_sec = to_seconds(wtime)
    btime_sec = to_seconds(btime)
    winc_sec = to_seconds(winc)
    binc_sec = to_seconds(binc)

    # Determine which color we are and get our time/increment
    if board.turn == chess.WHITE:
        our_time = wtime_sec
        our_inc = winc_sec
    else:
        our_time = btime_sec
        our_inc = binc_sec

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

    # CRITICAL: Verify it's actually our turn before making a move
    if board.turn != our_color:
        print(f"⏳ Waiting for opponent's move... (Turn: {'White' if board.turn == chess.WHITE else 'Black'}, We are: {'White' if our_color == chess.WHITE else 'Black'})")
        return

    # Double-check we're not moving on a completed game
    if state['status'] != 'started':
        print(f"⚠️  Game already ended with status: {state['status']}")
        return

    # It's our turn! Calculate time limit
    wtime = state.get('wtime', 60000)
    btime = state.get('btime', 60000)
    winc = state.get('winc', 0)
    binc = state.get('binc', 0)

    time_limit = calculate_time_limit(wtime, btime, winc, binc, board)

    # Convert time values to seconds for display (use same helper as calculate_time_limit)
    def to_seconds(time_value):
        if time_value is None:
            return 0.0
        if hasattr(time_value, 'total_seconds'):
            return time_value.total_seconds()
        else:
            return float(time_value) / 1000.0

    wtime_sec = to_seconds(wtime)
    btime_sec = to_seconds(btime)

    print(f"\n{'─'*60}")
    print(f"🧠 Bot's turn ({'White' if our_color == chess.WHITE else 'Black'})")
    print(f"⏱️  Time remaining: {wtime_sec:.1f}s (W) | {btime_sec:.1f}s (B)")
    print(f"⏱️  Time limit for this move: {time_limit:.2f}s")
    print(f"📊 Position: {len(board.move_stack)} moves played")
    print(f"📊 Board FEN: {board.fen()}")
    print(f"📊 Turn to move: {'White' if board.turn == chess.WHITE else 'Black'}")
    print(f"📊 Bot color: {'White' if our_color == chess.WHITE else 'Black'}")
    print(f"{'─'*60}")

    # Calculate the move using our engine
    start_time = time.time()

    # Use time-limited iterative deepening for ALL phases (middlegame and endgame)
    # This prevents timeouts on Koyeb's slower CPUs and allows deeper search when time permits
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

    Accepts all standard chess games (Rapid, Blitz, Classical, etc.)
    Optimized for Rapid time controls (10+5) but will play any time control.

    CONCURRENCY: Only accepts challenges when idle (max 1 game at a time)

    Args:
        event: The challenge event dict
    """
    global active_games

    challenge_id = event['challenge']['id']
    challenger = event['challenge']['challenger']['name']
    variant = event['challenge']['variant']['name']
    time_control = event['challenge'].get('timeControl', {})

    # Parse time control for display
    limit = time_control.get('limit', 0) // 60 if time_control else 0  # Convert seconds to minutes
    increment = time_control.get('increment', 0) if time_control else 0

    print(f"\n📨 Challenge received from {challenger}")
    print(f"   Variant: {variant}")
    print(f"   Time: {limit}+{increment}" if time_control else "   Time: Unlimited")

    # CRITICAL: Only accept if we're idle (no active games)
    # Python is single-threaded - minimax search blocks everything
    if len(active_games) > 0:
        print(f"⚠️  Declined: Already playing {len(active_games)} game(s)")
        print(f"   Active games: {list(active_games.keys())}")
        try:
            client.bots.decline_challenge(challenge_id, reason=berserk.enums.DeclineReason.LATER)
        except:
            pass
        return

    # Accept standard chess challenges only (all time controls)
    # Note: Engine is optimized for Rapid (10+5) but will play Blitz/Classical
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
# CONCURRENCY LIMIT: 1 game at a time
# Python is single-threaded - minimax search blocks all other operations
# Playing multiple games simultaneously would cause 30-second abort timeouts
# ============================================================================

# Track currently playing games (game_id -> color)
# This is used to enforce max_concurrency = 1
currently_playing = set()

def is_bot_idle():
    """Check if bot is currently idle (not in any active games)"""
    global active_games
    try:
        # Check our internal tracking first (more reliable)
        if len(active_games) > 0:
            return False

        # Double-check with Lichess API
        ongoing = list(client.games.get_ongoing())
        return len(ongoing) == 0
    except:
        # If API call fails, be conservative and assume we're busy
        return len(active_games) == 0

def find_and_challenge_bot():
    """
    Find an online bot and challenge them to a game.

    IMPORTANT: Only challenges other BOTS, never humans (Lichess TOS requirement)
    CONCURRENCY: Only sends challenge if bot is idle (no active games)
    """
    global active_games

    # Safety check: Don't send challenges if already in a game
    if len(active_games) > 0:
        print(f"⚠️  Skipping challenge: Already in {len(active_games)} game(s)")
        return

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

                # Send challenge (10+5 Rapid, Rated)
                # Rapid time control gives enough time for depth-5 engine (5-15 sec/move)
                challenge_response = client.challenges.create(
                    target_username,
                    rated=True,  # Rated games to build rating
                    clock_limit=600,  # 10 minutes
                    clock_increment=5,  # 5 second increment
                    color='random',
                    variant='standard'
                )

                print(f"✓ Challenge sent to {target_username} (10+5 Rapid)!")

        except Exception as e:
            print(f"⚠️  Could not challenge bot: {e}")

    except Exception as e:
        print(f"⚠️  Error in hunter mode: {e}")

def hunter_loop():
    """
    Background thread that periodically challenges other bots when idle.

    Runs every 2 minutes to check if bot is idle and seeks new games.
    MAX CONCURRENCY: 1 game at a time (Python single-threaded constraint)
    """
    print("🏹 Hunter mode activated - will seek games when idle (max 1 at a time)")

    while True:
        try:
            # Wait 2 minutes between checks
            time.sleep(120)

            # Check if we're idle
            if is_bot_idle():
                print("\n💤 Bot is idle, looking for opponents...")
                find_and_challenge_bot()
            else:
                global active_games
                print(f"⚔️  Bot is currently playing ({len(active_games)} active game(s))")
                if active_games:
                    print(f"   Active: {list(active_games.keys())}")

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
    print(f"🎯 Max concurrency: 1 game at a time (single-threaded)")
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
