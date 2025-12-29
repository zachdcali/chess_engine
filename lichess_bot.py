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
from cpp_engine_bridge import CppEngineAgent

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

# Cache bot identity at startup to avoid repeated API calls during games
BOT_ACCOUNT = client.account.get()
BOT_ID = BOT_ACCOUNT['id']  # Lowercase ID is more reliable than 'username'
print(f"🤖 Bot initialized as: {BOT_ACCOUNT['username']} ({BOT_ID})")

# Initialize the C++ chess engine (depth 9 for Rapid, depth 8 for Blitz)
# Depth is set dynamically based on time control during gameplay
engine = CppEngineAgent(depth=9, engine_path="./pasta_engine")
print("✓ C++ Engine ready (default depth 9)!\n")

# Store game-specific information (game_id -> color mapping)
active_games = {}
is_playing = False  # Global lock for max 1 game at a time
game_start_times = {}  # Track when games start for watchdog
game_time_controls = {}  # Track time control per game (for depth selection)

# Thread safety: Lock to ensure only ONE thread accesses the engine at a time
# This prevents race conditions where multiple games try to use the C++ engine simultaneously
engine_lock = threading.Lock()

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
    global is_playing, game_start_times

    try:
        # NOTE: is_playing is already set to True in main() before this thread starts
        # This prevents race conditions where multiple gameStart events overlap
        game_start_times[game_id] = time.time()  # Track when game started

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

            # OPPONENT TIMEOUT WATCHDOG: Check if opponent hasn't moved after 5 minutes
            # This prevents getting stuck when opponent abandons game
            if game_id in game_start_times and game_id in active_games:
                elapsed = time.time() - game_start_times[game_id]
                our_color = active_games[game_id]
                moves = event.get('state', {}).get('moves', '') or event.get('moves', '')
                move_list = moves.split() if moves else []
                move_count = len(move_list)

                # Abort if opponent hasn't moved after 5 minutes:
                # Case 1: We're Black, opponent (White) hasn't made first move (0 moves total)
                # Case 2: We're White, we moved, opponent (Black) hasn't responded (1 move total)
                should_abort = False
                if elapsed > 300:  # 5 minutes
                    if our_color == chess.BLACK and move_count == 0:
                        print(f"⏰ WATCHDOG: White hasn't made first move after 5 minutes. Aborting...")
                        should_abort = True
                    elif our_color == chess.WHITE and move_count == 1:
                        print(f"⏰ WATCHDOG: Black hasn't responded to 1.{move_list[0]} after 5 minutes. Aborting...")
                        should_abort = True

                if should_abort:
                    try:
                        client.bots.abort_game(game_id)
                    except:
                        pass  # Game might already be over
                    break

            # Check if game ended
            status = event.get('status') or event.get('state', {}).get('status')
            if status and status != 'started':
                break

    except Exception as e:
        print(f"❌ Stream Error in game {game_id}: {e}")
        import traceback
        traceback.print_exc()
        print(f"⚠️  Game thread crashed - cleaning up to prevent zombie state")
    finally:
        # CRITICAL: ALWAYS release the lock when game ends (even if crashed)
        # This prevents "zombie state" where bot appears busy but isn't playing
        print(f"\n🧹 Cleanup for game {game_id}:")
        print(f"   - Releasing is_playing lock")
        is_playing = False

        if game_id in active_games:
            print(f"   - Removing from active_games")
            del active_games[game_id]

        if game_id in game_start_times:
            print(f"   - Removing from game_start_times")
            del game_start_times[game_id]

        if game_id in game_time_controls:
            print(f"   - Removing from game_time_controls")
            del game_time_controls[game_id]

        print(f"✓ Cleanup complete - bot is now idle")
        print(f"🏁 Game Finished: {game_id}\n")


def handle_game_state(game_id, state, full_event=None):
    """
    Handle a game state update and make a move if it's our turn.

    Args:
        game_id: The Lichess game ID
        state: The game state dict
        full_event: The full event dict (only on first call with gameFull)
    """
    global active_games, game_time_controls

    # Determine our color (from full_event on first call, then from stored info)
    if full_event:
        # First time seeing this game - determine and store our color using ID (more reliable)
        white_id = full_event.get('white', {}).get('id', '').lower()
        black_id = full_event.get('black', {}).get('id', '').lower()

        white_player = full_event.get('white', {}).get('name', 'Unknown')
        black_player = full_event.get('black', {}).get('name', 'Unknown')
        print(f"⚔️  White: {white_player} vs Black: {black_player}")

        if BOT_ID == white_id:
            our_color = chess.WHITE
        elif BOT_ID == black_id:
            our_color = chess.BLACK
        else:
            print("⚠️  Could not determine bot color!")
            return

        # Extract and store time control for depth selection
        clock = full_event.get('clock')
        if clock:
            initial_time = clock.get('initial', 0) // 1000  # Convert ms to seconds
            increment = clock.get('increment', 0) // 1000
            game_time_controls[game_id] = (initial_time, increment)
            print(f"⏱️  Time control: {initial_time // 60}+{increment}")
        else:
            game_time_controls[game_id] = (0, 0)  # Unlimited or correspondence

        # Store for future state updates
        active_games[game_id] = our_color

        # For gameFull events, the actual state is nested
        actual_state = full_event.get('state', state)
    else:
        # Retrieve our color from stored info
        our_color = active_games.get(game_id)
        if our_color is None:
            print("⚠️  Game color not found in active games!")
            return
        actual_state = state

    # Get the moves string and convert to a board position
    moves_str = actual_state.get('moves', '')
    board = chess.Board()

    if moves_str:
        # Apply all moves to the board
        for move_uci in moves_str.split():
            board.push_uci(move_uci)

    # Check if game is over
    if actual_state['status'] != 'started':
        print(f"\n🏁 Game Over! Status: {actual_state['status']}")
        # Clean up
        if game_id in active_games:
            del active_games[game_id]
        if game_id in game_time_controls:
            del game_time_controls[game_id]
        return

    # CRITICAL: Verify it's actually our turn before making a move
    if board.turn != our_color:
        print(f"⏳ Waiting for opponent's move... (Turn: {'White' if board.turn == chess.WHITE else 'Black'}, We are: {'White' if our_color == chess.WHITE else 'Black'})")
        return

    # Double-check we're not moving on a completed game
    if actual_state['status'] != 'started':
        print(f"⚠️  Game already ended with status: {actual_state['status']}")
        return

    # It's our turn! Calculate time limit
    wtime = actual_state.get('wtime', 60000)
    btime = actual_state.get('btime', 60000)
    winc = actual_state.get('winc', 0)
    binc = actual_state.get('binc', 0)

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

    # Determine search depth based on time control
    # Blitz (< 5 minutes initial): depth 8 (~0.7s/move)
    # Rapid (≥ 5 minutes): depth 9 (~2s/move)
    time_control = game_time_controls.get(game_id, (600, 5))  # Default to 10+5
    initial_time, increment = time_control

    if initial_time < 300:  # Less than 5 minutes = Blitz
        target_depth = 8
        print(f"🏃 Blitz mode: Using depth {target_depth}")
    else:  # 5+ minutes = Rapid/Classical
        target_depth = 9
        print(f"🧠 Rapid mode: Using depth {target_depth}")

    # Calculate the move using our engine
    start_time = time.time()

    # Use time-limited iterative deepening for ALL phases (middlegame and endgame)
    # This prevents timeouts on Koyeb's slower CPUs and allows deeper search when time permits
    # CRITICAL: Lock the engine to prevent race conditions from simultaneous access
    with engine_lock:
        move, score = engine.select_move(board, endgame_time_limit=time_limit, target_depth=target_depth)

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

    # Make the move on Lichess with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client.bots.make_move(game_id, move.uci())
            print(f"📤 Move sent to Lichess: {move.uci()}")
            break  # Success - exit retry loop
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)  # Exponential backoff: 0.5s, 1s, 2s
                print(f"⚠️  Move send failed (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"   Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ Error making move {move.uci()} after {max_retries} attempts: {e}")
                print(f"⚠️  This may cause timeout loss if move wasn't transmitted")
                import traceback
                traceback.print_exc()


def accept_challenge(event):
    """
    Automatically accept incoming challenges.

    Accepts all standard chess games (Rapid, Blitz, Classical, etc.)
    Optimized for Rapid time controls (10+5) but will play any time control.

    CONCURRENCY: Only accepts challenges when idle (max 1 game at a time)

    Args:
        event: The challenge event dict
    """
    global is_playing

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
    if is_playing:
        print(f"⚠️  Declined: Already playing a game")
        try:
            client.bots.decline_challenge(challenge_id, reason=berserk.enums.DeclineReason.LATER)
        except:
            pass
        return

    # Accept standard chess challenges only (all time controls)
    # Note: Engine is optimized for Classical (30+20) but will play any time control
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

def is_bot_idle():
    """Check if bot is currently idle (not in any active games)"""
    global is_playing
    try:
        # Check our internal tracking first (more reliable)
        if is_playing:
            return False

        # Double-check with Lichess API
        ongoing = list(client.games.get_ongoing())
        return len(ongoing) == 0
    except:
        # If API call fails, be conservative and assume we're busy
        return not is_playing

def find_and_challenge_bot():
    """
    Find an online bot and challenge them to a game.

    IMPORTANT: Only challenges other BOTS, never humans (Lichess TOS requirement)
    CONCURRENCY: Only sends challenge if bot is idle (no active games)
    """
    global is_playing

    # Safety check: Don't send challenges if already in a game
    if is_playing:
        print(f"⚠️  Skipping challenge: Already in a game")
        return

    # CRITICAL FIX: Make live API call to verify no ongoing games
    # This prevents challenging while a game is "finishing" but not fully closed
    try:
        ongoing_games = list(client.games.get_ongoing(count=5))
        if len(ongoing_games) > 0:
            print(f"⚠️  Skipping challenge: Found {len(ongoing_games)} ongoing game(s) via API")
            return
    except Exception as e:
        print(f"⚠️  Could not verify ongoing games: {e}")
        # If API call fails, be conservative and don't challenge
        return

    try:
        # Get online bots from Lichess bot endpoint
        # We use BOT_ID (cached at startup) to exclude ourselves
        try:
            response = requests.get("https://lichess.org/api/bot/online", timeout=10)
            if response.status_code == 200:
                online_bots_list = []
                for line in response.text.strip().split('\n'):
                    if line:
                        bot_data = json.loads(line)
                        # Exclude ourselves using cached BOT_ID
                        if bot_data.get('id', '').lower() != BOT_ID:
                            online_bots_list.append(bot_data)

                if not online_bots_list:
                    print("💤 No online bots found to challenge")
                    return

                # Pick a random bot from the list
                target_bot = random.choice(online_bots_list)
                target_username = target_bot['username']

                print(f"\n🎯 Challenging bot: {target_username}")

                # Send challenge (10+5 Rapid, Rated)
                # Rapid time control - C++ engine at depth 8 is fast enough
                client.challenges.create(
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
                print(f"⚔️  Bot is currently playing a game")

        except Exception as e:
            print(f"⚠️  Hunter loop error: {e}")
            time.sleep(120)  # Wait before retrying

def start_hunter_mode():
    """Start the hunter mode in a background thread"""
    hunter_thread = threading.Thread(target=hunter_loop, daemon=True)
    hunter_thread.start()
    print("✓ Hunter mode started - bot will actively seek games\n")


def cleanup_ongoing_games():
    """
    Clean up any ongoing games from previous session at startup.
    This prevents the bot from being stuck in a zombie game.
    """
    global is_playing

    print("🧹 Checking for ongoing games from previous session...")
    try:
        ongoing = client.games.get_ongoing(count=10)
        if ongoing:
            print(f"⚠️  Found {len(ongoing)} ongoing game(s) from previous session")
            for game in ongoing:
                game_id = game['gameId']
                print(f"   🗑️  Resigning game: {game_id}")
                try:
                    # Try to resign (safer than abort for old games)
                    client.bots.resign_game(game_id)
                except Exception as e:
                    print(f"   ⚠️  Could not resign {game_id}: {e}")
                    try:
                        # If resign fails, try abort
                        client.bots.abort_game(game_id)
                    except:
                        pass  # Game might already be over
            print("✓ Cleanup complete - starting fresh\n")
        else:
            print("✓ No ongoing games - clean state\n")

        # Ensure is_playing is False after cleanup
        is_playing = False
    except Exception as e:
        print(f"⚠️  Error during cleanup: {e}\n")
        is_playing = False  # Ensure lock is released


def main():
    """
    Main bot loop: listen for events and handle challenges/games.
    """
    global is_playing  # Needed because we modify is_playing in this function

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

    # Use cached account info (already fetched at startup)
    username = BOT_ACCOUNT['username']
    print(f"{'='*60}")
    print(f"🤖 PestoPasta-Bot ({username}) is now online!")
    print(f"{'='*60}")
    print(f"📡 Listening for challenges and games...")
    print(f"🎯 Max concurrency: 1 game at a time (single-threaded)")
    print(f"💡 Go to https://lichess.org/@/{username} to see your profile")
    print(f"{'='*60}\n")

    # Clean up any zombie games from previous session
    cleanup_ongoing_games()

    # Start hunter mode - actively seek games with other bots
    start_hunter_mode()

    # Stream incoming events (challenges and games) with reconnect logic
    # If stream closes, reconnect and continue (prevents bot from exiting)
    while True:
        try:
            print("📡 Connecting to Lichess event stream...")
            for event in client.bots.stream_incoming_events():
                if event['type'] == 'challenge':
                    # New challenge received
                    accept_challenge(event)
                elif event['type'] == 'gameStart':
                    # Game is starting - run in a separate thread so event loop continues
                    game_id = event['game']['id']

                    # FIX RACE CONDITION: Check if already playing before starting new thread
                    if is_playing:
                        print(f"⚠️  Ignoring gameStart for {game_id} - already in a game.")
                        print(f"⚠️  This game will likely be aborted by Lichess due to no moves.")
                        continue

                    print(f"\n🎮 Game starting: {game_id}")

                    # Set lock IMMEDIATELY to prevent another gameStart event from racing
                    is_playing = True

                    # Run game in thread so we can still receive events (abort, chat, etc.)
                    game_thread = threading.Thread(target=play_game, args=(game_id,), daemon=False)
                    game_thread.start()
                elif event['type'] == 'gameFinish':
                    # Game finished
                    game_id = event['game']['id']
                    print(f"\n🏁 Game finished: {game_id}\n")
                    print(f"{'='*60}")
                    print(f"📡 Ready for next challenge...")
                    print(f"{'='*60}\n")

            # If we reach here, stream ended - reconnect after delay
            print("⚠️  Event stream ended. Reconnecting in 5 seconds...")
            time.sleep(5)

        except Exception as e:
            print(f"❌ Error in event stream: {e}")
            print("🔄 Reconnecting in 10 seconds...")
            time.sleep(10)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Bot shutting down... Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
