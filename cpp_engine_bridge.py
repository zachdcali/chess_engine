"""
C++ Engine Bridge for Lichess Bot

This module provides a Python interface to the C++ chess engine via UCI protocol.
Drop-in replacement for agent_minimax.MinimaxAgent - same interface, 50-100x faster!
"""

import subprocess
import chess

class CppEngineAgent:
    """
    Python wrapper for the C++ UCI engine.

    Compatible with existing lichess_bot.py - same interface as MinimaxAgent.
    """

    def __init__(self, depth=5, engine_path="./pasta_engine"):
        """
        Initialize the C++ engine.

        Args:
            depth: Default search depth (can reach 8-10 with C++ speed)
            engine_path: Path to compiled C++ engine executable
        """
        self.depth = depth
        self.engine_path = engine_path

        # Start the engine process
        self.process = subprocess.Popen(
            [engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Initialize UCI
        self._send_command("uci")
        self._wait_for("uciok")
        self._send_command("isready")
        self._wait_for("readyok")

        print(f"✓ C++ Engine initialized (default depth: {depth})")

    def _send_command(self, cmd):
        """Send a command to the engine."""
        self.process.stdin.write(cmd + "\n")
        self.process.stdin.flush()

    def _wait_for(self, expected):
        """Wait for a specific response from the engine."""
        while True:
            line = self.process.stdout.readline().strip()
            if line == expected:
                return
            if line.startswith("info"):
                print(f"  {line}")  # Print search info

    def _read_until_bestmove(self):
        """Read engine output until we get the best move. Returns (move_uci, score)."""
        best_score = None
        best_move_uci = None

        while True:
            line = self.process.stdout.readline().strip()
            if line.startswith("info"):
                # Parse UCI info line
                parts = line.split()
                info = {}

                i = 1  # Skip "info"
                while i < len(parts):
                    if parts[i] == "depth" and i + 1 < len(parts):
                        info['depth'] = int(parts[i + 1])
                        i += 2
                    elif parts[i] == "score" and i + 2 < len(parts):
                        info['score'] = int(parts[i + 2])  # Skip "cp"
                        i += 3
                    elif parts[i] == "nodes" and i + 1 < len(parts):
                        info['nodes'] = int(parts[i + 1])
                        i += 2
                    elif parts[i] == "time" and i + 1 < len(parts):
                        info['time'] = int(parts[i + 1])
                        i += 2
                    elif parts[i] == "nps" and i + 1 < len(parts):
                        info['nps'] = int(parts[i + 1])
                        i += 2
                    elif parts[i] == "pv" and i + 1 < len(parts):
                        info['pv'] = parts[i + 1]
                        i += 2
                    elif parts[i] == "tthits" and i + 1 < len(parts):
                        info['tthits'] = int(parts[i + 1])
                        i += 2
                    elif parts[i] == "ttrate" and i + 1 < len(parts):
                        info['ttrate'] = int(parts[i + 1])
                        i += 2
                    elif parts[i] == "ttcutoffs" and i + 1 < len(parts):
                        info['ttcutoffs'] = int(parts[i + 1])
                        i += 2
                    elif parts[i] == "abcutoffs" and i + 1 < len(parts):
                        info['abcutoffs'] = int(parts[i + 1])
                        i += 2
                    elif parts[i] == "qsnodes" and i + 1 < len(parts):
                        info['qsnodes'] = int(parts[i + 1])
                        i += 2
                    elif parts[i] == "qspct" and i + 1 < len(parts):
                        info['qspct'] = int(parts[i + 1])
                        i += 2
                    else:
                        i += 1

                # Format like Python version
                if 'depth' in info:
                    depth = info['depth']
                    score = info.get('score', 0)
                    nodes = info.get('nodes', 0)
                    time_ms = info.get('time', 1)
                    time_s = time_ms / 1000.0
                    nps = info.get('nps', 0)
                    pv = info.get('pv', '?')

                    tthits = info.get('tthits', 0)
                    ttrate = info.get('ttrate', 0)
                    ttcutoffs = info.get('ttcutoffs', 0)
                    abcutoffs = info.get('abcutoffs', 0)
                    qsnodes = info.get('qsnodes', 0)
                    qspct = info.get('qspct', 0)

                    print(f"\n📊 Depth {depth} (Elapsed: {time_s:.1f}s) | Mode: C++")
                    print(f"  ✓ COMPLETE | Best: {pv} | Score: {score:+d}")
                    print(f"  ⏱️  Time: {time_s:.2f}s | Nodes: {nodes:,} | Speed: {nps:,} nodes/sec")
                    print(f"  🗃 TT hits: {tthits:,} ({ttrate:.1f}%) | Cutoffs: {ttcutoffs:,}")
                    print(f"  ✂️ Alpha-beta cutoffs: {abcutoffs:,}")
                    print(f"  🎯 Quiescence nodes: {qsnodes:,} ({qspct:.1f}% of total)")

                    # Store best score
                    best_score = score
                    best_move_uci = pv

            elif line.startswith("bestmove"):
                # Parse: "bestmove e2e4"
                parts = line.split()
                if len(parts) >= 2:
                    return (parts[1], best_score)
                return (None, None)

    def select_move(self, board, time_limit=45.0, target_depth=None, endgame_time_limit=5.0):
        """
        Select the best move using the C++ engine.

        Compatible with MinimaxAgent.select_move() interface.

        Args:
            board: python-chess Board object
            time_limit: Time limit (not used, kept for compatibility)
            target_depth: Optional depth override
            endgame_time_limit: Time limit for this specific move

        Returns:
            Tuple of (move, score) where score may be None
        """
        # Calculate game phase (0 = endgame, 24 = opening)
        phase_values = {
            chess.PAWN: 0,
            chess.KNIGHT: 1,
            chess.BISHOP: 1,
            chess.ROOK: 2,
            chess.QUEEN: 4,
            chess.KING: 0
        }
        phase = sum(phase_values[piece.piece_type] for piece in board.piece_map().values())
        phase = min(phase, 24)

        # Send position to engine
        fen = board.fen()
        self._send_command(f"position fen {fen}")

        # Decide search mode based on game phase
        # Endgame (phase < 10): Use time-based search to go deeper
        # Opening/Middlegame: Use fixed depth
        if phase < 10 and not target_depth:
            # Endgame: time-based search (5 seconds = 5000 ms)
            movetime_ms = int(endgame_time_limit * 1000)
            print(f"\n🚀 C++ Engine searching (endgame, {endgame_time_limit}s time limit, phase={phase}/24)...")
            self._send_command(f"go movetime {movetime_ms}")
        else:
            # Opening/Middlegame: depth-based search
            search_depth = target_depth if target_depth else self.depth
            print(f"\n🚀 C++ Engine searching (depth {search_depth}, phase={phase}/24)...")
            self._send_command(f"go depth {search_depth}")

        # Get best move and score
        move_uci, score = self._read_until_bestmove()

        if not move_uci:
            print("❌ C++ Engine returned no move!")
            return (None, None)

        # Convert UCI string to python-chess Move
        try:
            move = chess.Move.from_uci(move_uci)

            # Validate move is legal
            if move not in board.legal_moves:
                print(f"⚠️ C++ Engine returned illegal move: {move_uci}")
                return (None, None)

            print(f"✓ C++ Engine selected: {move_uci} (score: {score if score else 'N/A'} cp)")

            # Return (move, score)
            return (move, score)

        except ValueError:
            print(f"❌ Invalid UCI move from C++ engine: {move_uci}")
            return (None, None)

    def clear_tt(self):
        """
        Clear the transposition table (start of new game).

        Compatible with MinimaxAgent.clear_tt() interface.
        """
        self._send_command("ucinewgame")
        print("🧹 C++ Engine transposition table cleared")

    def __del__(self):
        """Clean up the engine process."""
        if hasattr(self, 'process'):
            self._send_command("quit")
            self.process.wait(timeout=1)


# ============================================================================
# EXAMPLE: How to integrate with lichess_bot.py
# ============================================================================

if __name__ == "__main__":
    # Test the bridge
    print("Testing C++ Engine Bridge...")

    # Initialize engine (depth 6 is achievable with C++)
    engine = CppEngineAgent(depth=6, engine_path="./pasta_engine")

    # Test on starting position
    board = chess.Board()
    print(f"\nPosition: {board.fen()}")

    # Get best move
    move, score = engine.select_move(board)

    if move:
        print(f"\n✓ Best move: {move}")
        print(f"  Score: {score if score else 'N/A'}")
    else:
        print("\n❌ Failed to get move")

    # Clean up
    del engine
    print("\n✓ Test complete")


# ============================================================================
# TO USE IN LICHESS_BOT.PY:
# ============================================================================
"""
OPTION 1: Replace the import (easiest)

Change this line in lichess_bot.py:
    from agent_minimax import MinimaxAgent

To:
    from cpp_engine_bridge import CppEngineAgent as MinimaxAgent

And change:
    engine = MinimaxAgent(depth=5)

To:
    engine = CppEngineAgent(depth=7)  # Can go deeper with C++!


OPTION 2: Gradual migration (safer)

Keep both engines and let user choose:

    import os
    from agent_minimax import MinimaxAgent as PythonEngine
    from cpp_engine_bridge import CppEngineAgent as CppEngine

    # Use C++ if available, fallback to Python
    if os.path.exists("./pasta_engine"):
        print("Using C++ Engine (Fast)")
        engine = CppEngine(depth=7)
    else:
        print("Using Python Engine (Fallback)")
        engine = PythonEngine(depth=5)
"""
