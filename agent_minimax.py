import chess
import chess.polyglot
import time
import gc

# TRANSPOSITION TABLE FLAGS
# These indicate what type of score we stored
TT_EXACT = 0      # Exact score (searched all moves)
TT_LOWERBOUND = 1 # Beta cutoff / fail-high (actual score >= this)
TT_UPPERBOUND = 2 # Alpha cutoff / fail-low (actual score <= this)

# ============================================================================
# PeSTO'S PIECE-SQUARE TABLES (Middlegame and Endgame)
# Source: https://www.chessprogramming.org/PeSTO%27s_Evaluation_Function
# Tables are from White's perspective (index 0 = a1, index 63 = h8)
# ============================================================================

# PAWNS
PAWN_MG = [
      0,   0,   0,   0,   0,   0,  0,   0,
     98, 134,  61,  95,  68, 126, 34, -11,
     -6,   7,  26,  31,  65,  56, 25, -20,
    -14,  13,   6,  21,  23,  12, 17, -23,
    -27,  -2,  -5,  12,  17,   6, 10, -25,
    -26,  -4,  -4, -10,   3,   3, 33, -12,
    -35,  -1, -20, -23, -15,  24, 38, -22,
      0,   0,   0,   0,   0,   0,  0,   0,
]

PAWN_EG = [
      0,   0,   0,   0,   0,   0,   0,   0,
    178, 173, 158, 134, 147, 132, 165, 187,
     94, 100,  85,  67,  56,  53,  82,  84,
     32,  24,  13,   5,  -2,   4,  17,  17,
     13,   9,  -3,  -7,  -7,  -8,   3,  -1,
      4,   7,  -6,   1,   0,  -5,  -1,  -8,
     13,   8,   8,  10,  13,   0,   2,  -7,
      0,   0,   0,   0,   0,   0,   0,   0,
]

# KNIGHTS
KNIGHT_MG = [
    -167, -89, -34, -49,  61, -97, -15, -107,
     -73, -41,  72,  36,  23,  62,   7,  -17,
     -47,  60,  37,  65,  84, 129,  73,   44,
      -9,  17,  19,  53,  37,  69,  18,   22,
     -13,   4,  16,  13,  28,  19,  21,   -8,
     -23,  -9,  12,  10,  19,  17,  25,  -16,
     -29, -53, -12,  -3,  -1,  18, -14,  -19,
    -105, -21, -58, -33, -17, -28, -19,  -23,
]

KNIGHT_EG = [
    -58, -38, -13, -28, -31, -27, -63, -99,
    -25,  -8, -25,  -2,  -9, -25, -24, -52,
    -24, -20,  10,   9,  -1,  -9, -19, -41,
    -17,   3,  22,  22,  22,  11,   8, -18,
    -18,  -6,  16,  25,  16,  17,   4, -18,
    -23,  -3,  -1,  15,  10,  -3, -20, -22,
    -42, -20, -10,  -5,  -2, -20, -23, -44,
    -29, -51, -23, -15, -22, -18, -50, -64,
]

# BISHOPS
BISHOP_MG = [
    -29,   4, -82, -37, -25, -42,   7,  -8,
    -26,  16, -18, -13,  30,  59,  18, -47,
    -16,  37,  43,  40,  35,  50,  37,  -2,
     -4,   5,  19,  50,  37,  37,   7,  -2,
     -6,  13,  13,  26,  34,  12,  10,   4,
      0,  15,  15,  15,  14,  27,  18,  10,
      4,  15,  16,   0,   7,  21,  33,   1,
    -33,  -3, -14, -21, -13, -12, -39, -21,
]

BISHOP_EG = [
    -14, -21, -11,  -8, -7,  -9, -17, -24,
     -8,  -4,   7, -12, -3, -13,  -4, -14,
      2,  -8,   0,  -1, -2,   6,   0,   4,
     -3,   9,  12,   9, 14,  10,   3,   2,
     -6,   3,  13,  19,  7,  10,  -3,  -9,
    -12,  -3,   8,  10, 13,   3,  -7, -15,
    -14, -18,  -7,  -1,  4,  -9, -15, -27,
    -23,  -9, -23,  -5, -9, -16,  -5, -17,
]

# ROOKS
ROOK_MG = [
     32,  42,  32,  51, 63,  9,  31,  43,
     27,  32,  58,  62, 80, 67,  26,  44,
     -5,  19,  26,  36, 17, 45,  61,  16,
    -24, -11,   7,  26, 24, 35,  -8, -20,
    -36, -26, -12,  -1,  9, -7,   6, -23,
    -45, -25, -16, -17,  3,  0,  -5, -33,
    -44, -16, -20,  -9, -1, 11,  -6, -71,
    -19, -13,   1,  17, 16,  7, -37, -26,
]

ROOK_EG = [
    13, 10, 18, 15, 12,  12,   8,   5,
    11, 13, 13, 11, -3,   3,   8,   3,
     7,  7,  7,  5,  4,  -3,  -5,  -3,
     4,  3, 13,  1,  2,   1,  -1,   2,
     3,  5,  8,  4, -5,  -6,  -8, -11,
    -4,  0, -5, -1, -7, -12,  -8, -16,
    -6, -6,  0,  2, -9,  -9, -11,  -3,
    -9,  2,  3, -1, -5, -13,   4, -20,
]

# QUEENS
QUEEN_MG = [
    -28,   0,  29,  12,  59,  44,  43,  45,
    -24, -39,  -5,   1, -16,  57,  28,  54,
    -13, -17,   7,   8,  29,  56,  47,  57,
    -27, -27, -16, -16,  -1,  17,  -2,   1,
     -9, -26,  -9, -10,  -2,  -4,   3,  -3,
    -14,   2, -11,  -2,  -5,   2,  14,   5,
    -35,  -8,  11,   2,   8,  15,  -3,   1,
     -1, -18,  -9,  10, -15, -25, -31, -50,
]

QUEEN_EG = [
     -9,  22,  22,  27,  27,  19,  10,  20,
    -17,  20,  32,  41,  58,  25,  30,   0,
    -20,   6,   9,  49,  47,  35,  19,   9,
      3,  22,  24,  45,  57,  40,  57,  36,
    -18,  28,  19,  47,  31,  34,  39,  23,
    -16, -27,  15,   6,   9,  17,  10,   5,
    -22, -23, -30, -16, -16, -23, -36, -32,
    -33, -28, -22, -43,  -5, -32, -20, -41,
]

# KINGS
KING_MG = [
    -65,  23,  16, -15, -56, -34,   2,  13,
     29,  -1, -20,  -7,  -8,  -4, -38, -29,
     -9,  24,   2, -16, -20,   6,  22, -22,
    -17, -20, -12, -27, -30, -25, -14, -36,
    -49,  -1, -27, -39, -46, -44, -33, -51,
    -14, -14, -22, -46, -44, -30, -15, -27,
      1,   7,  -8, -64, -43, -16,   9,   8,
    -15,  36,  12, -54,   8, -28,  24,  14,
]

KING_EG = [
    -74, -35, -18, -18, -11,  15,   4, -17,
    -12,  17,  14,  17,  17,  38,  23,  11,
     10,  17,  23,  15,  20,  45,  44,  13,
     -8,  22,  24,  27,  26,  33,  26,   3,
    -18,  -4,  21,  24,  27,  23,   9, -11,
    -19,  -3,  11,  21,  23,  16,   7,  -9,
    -27, -11,   4,  13,  14,   4,  -5, -17,
    -53, -34, -21, -11, -28, -14, -24, -43
]

# FIX: PeSTO tables are in visual order (Rank 8 first) but python-chess uses Rank 1 first
# We need to flip them so White's pieces read the correct values
def flip_ranks(pst):
    """Reverses a 64-element list from Rank 8-first to Rank 1-first."""
    flipped = []
    for r in range(7, -1, -1):
        flipped.extend(pst[r*8 : (r+1)*8])
    return flipped

# Apply rank flipping to all PST tables (CRITICAL FIX)
PAWN_MG, PAWN_EG = flip_ranks(PAWN_MG), flip_ranks(PAWN_EG)
KNIGHT_MG, KNIGHT_EG = flip_ranks(KNIGHT_MG), flip_ranks(KNIGHT_EG)
BISHOP_MG, BISHOP_EG = flip_ranks(BISHOP_MG), flip_ranks(BISHOP_EG)
ROOK_MG, ROOK_EG = flip_ranks(ROOK_MG), flip_ranks(ROOK_EG)
QUEEN_MG, QUEEN_EG = flip_ranks(QUEEN_MG), flip_ranks(QUEEN_EG)
KING_MG, KING_EG = flip_ranks(KING_MG), flip_ranks(KING_EG)

# ============================================================================
# PeSTO PIECE VALUES (Middlegame and Endgame)
# Source: https://www.chessprogramming.org/PeSTO%27s_Evaluation_Function
# These are tapered based on game phase for more accurate evaluation
# ============================================================================
PIECE_VALUE_MG = {
    chess.PAWN: 82,
    chess.KNIGHT: 337,
    chess.BISHOP: 365,
    chess.ROOK: 477,
    chess.QUEEN: 1025,
    chess.KING: 0
}

PIECE_VALUE_EG = {
    chess.PAWN: 94,
    chess.KNIGHT: 281,
    chess.BISHOP: 297,
    chess.ROOK: 512,
    chess.QUEEN: 936,
    chess.KING: 0
}

class MinimaxAgent:
    def __init__(self, depth = 2):
        self.depth = depth
        # centipawn values (1 pawn = 100)
        # King value is 0 - mate scoring is handled separately (±100000)
        self.piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0
        }

        # Transposition Table: stores previously evaluated positions
        # Key: zobrist hash of position
        # Value: dict with 'score', 'depth', 'flag', 'best_move'
        self.transposition_table = {}

        # Game phase piece values (for tapered evaluation)
        # Used to determine if we're in opening/middlegame or endgame
        self.phase_values = {
            chess.PAWN: 0,
            chess.KNIGHT: 1,
            chess.BISHOP: 1,
            chess.ROOK: 2,
            chess.QUEEN: 4,
            chess.KING: 0
        }

        # KILLER MOVES: 2 killer moves per ply (most recent quiet beta cutoffs)
        # killer_moves[ply][0] = primary killer, [1] = secondary killer
        MAX_PLY = 128
        self.killer_moves = [[None, None] for _ in range(MAX_PLY)]

        # HISTORY HEURISTIC: Track quiet moves that caused beta cutoffs
        # history[from_square][to_square] = score (higher = historically better)
        self.history_table = [[0 for _ in range(64)] for _ in range(64)]

        # PERFORMANCE TRACKING
        self.nodes_searched = 0      # Total nodes explored
        self.tt_hits = 0              # Transposition table hits
        self.tt_misses = 0            # Transposition table misses
        self.tt_cutoffs = 0           # Times TT caused a cutoff
        self.alpha_cutoffs = 0        # Alpha-beta pruning cutoffs
        self.quiescence_nodes = 0     # Nodes searched in quiescence

    def clear_tt(self):
        """
        Clear the transposition table.

        Call this at the start of a NEW GAME (not between moves in the same game).
        Clearing between moves removes major TT benefits like opponent response reuse.
        """
        self.transposition_table.clear()
        self.killer_moves = [[None, None] for _ in range(128)]
        self.history_table = [[0 for _ in range(64)] for _ in range(64)]

    def calculate_game_phase(self, board):
        """
        Calculate the game phase (0 = endgame, 24 = opening).

        Based on total non-pawn material:
        - Knights and Bishops contribute 1 point each
        - Rooks contribute 2 points each
        - Queens contribute 4 points each
        - Maximum phase (full board) = 24

        Returns:
            int: Game phase value (0-24)
        """
        phase = 0
        # OPTIMIZED: Use piece_map() to iterate only occupied squares
        for piece in board.piece_map().values():
            phase += self.phase_values[piece.piece_type]

        # Total phase can be more than 24 with promotions, cap it
        return min(phase, 24)

    # Move ordering: Score moves to search better moves first (for alpha-beta efficiency)
    def score_move(self, board, move, ply=0):
        """
        Give each move a score so we can sort them.
        Higher scores = search first (better for alpha-beta pruning)

        Ordering: TT move (handled separately) > Killers > Captures (MVV-LVA) > History > Rest

        OPTIMIZED: Removed check detection (board.push/is_check/pop) - too slow in Python
        """
        score = 0

        # 1. CAPTURES: Prioritize winning material
        if board.is_capture(move):
            # MVV-LVA: Most Valuable Victim - Least Valuable Attacker
            # Prefer QxP over PxQ (capturing queen with pawn is great!)
            victim_type = board.piece_type_at(move.to_square)
            attacker_type = board.piece_type_at(move.from_square)

            # Handle en passant (victim is None but it's still a pawn capture)
            if not victim_type and board.is_en_passant(move):
                victim_type = chess.PAWN

            if victim_type:
                score += self.piece_values[victim_type] * 10
                if attacker_type:
                    score -= self.piece_values[attacker_type]

        # 2. PROMOTIONS: Always good!
        if move.promotion:
            score += 9000

        # 3. KILLER MOVES: Quiet moves that caused beta cutoffs at this ply
        if not board.is_capture(move) and not move.promotion:
            if ply < len(self.killer_moves):
                if move == self.killer_moves[ply][0]:
                    score += 900000  # Primary killer
                elif move == self.killer_moves[ply][1]:
                    score += 800000  # Secondary killer

        # 4. HISTORY HEURISTIC: Quiet moves that historically caused cutoffs
        if not board.is_capture(move) and not move.promotion:
            score += self.history_table[move.from_square][move.to_square]

        return score

    # Evaluation function takes in a static board and outputs an evaluation score
    # Positive Eval Score = White winning, Negative Eval Score = Black winning
    def evaluate_board(self, board, ply_from_root=0):
        # 1. CHECK TERMINAL STATES
        if board.is_checkmate():
            # If it's White's turn and they are in checkmate, then Black won
            # Add ply_from_root so faster mates score better (closer to -100000)
            # Use 100000 (much higher than king value 20000) to clearly distinguish mate from material
            if board.turn == chess.WHITE:
                return -100000 + ply_from_root
            # If it's Black's turn and they are in checkmate, then White won
            # Subtract ply_from_root so faster mates score better (closer to +100000)
            else:
                return 100000 - ply_from_root
            
        # Stalemate or Draw (Insufficient material) is always 0 (Even)
        # Note: Removed can_claim_draw() - let engine choose whether to claim draws strategically
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        
        # CALCULATE GAME PHASE for tapered evaluation
        game_phase = self.calculate_game_phase(board)

        # TAPERED EVALUATION: Blend middlegame and endgame scores
        # In opening (phase=24): Use mostly middlegame tables
        # In endgame (phase=0): Use mostly endgame tables
        mg_score = 0  # Middlegame score
        eg_score = 0  # Endgame score

        # OPTIMIZED: Use piece_map() to iterate only occupied squares (~32) instead of all 64
        piece_map = board.piece_map()

        for square, piece in piece_map.items():
            # A. MATERIAL SCORE - Use PeSTO's phase-dependent piece values
            # King value is 0 in both MG and EG - mate scoring is separate (±100000)
            mg_material = PIECE_VALUE_MG[piece.piece_type]
            eg_material = PIECE_VALUE_EG[piece.piece_type]

            # B. POSITIONAL SCORE - Get both MG and EG table values
            # Select the correct tables based on piece type
            if piece.piece_type == chess.PAWN:
                mg_table = PAWN_MG
                eg_table = PAWN_EG
            elif piece.piece_type == chess.KNIGHT:
                mg_table = KNIGHT_MG
                eg_table = KNIGHT_EG
            elif piece.piece_type == chess.BISHOP:
                mg_table = BISHOP_MG
                eg_table = BISHOP_EG
            elif piece.piece_type == chess.ROOK:
                mg_table = ROOK_MG
                eg_table = ROOK_EG
            elif piece.piece_type == chess.QUEEN:
                mg_table = QUEEN_MG
                eg_table = QUEEN_EG
            elif piece.piece_type == chess.KING:
                mg_table = KING_MG
                eg_table = KING_EG
            else:
                # Fallback (should never happen)
                continue

            # C. COLOR ADJUSTMENT
            if piece.color == chess.WHITE:
                # White uses tables as-is (index 0 = a1, index 63 = h8)
                mg_pst = mg_table[square]
                eg_pst = eg_table[square]

                # Add to scores (White wants positive)
                mg_score += (mg_material + mg_pst)
                eg_score += (eg_material + eg_pst)
            else:
                # Black pieces: mirror the square index
                # (Black's a1 is White's a8, etc.)
                mirror_square = chess.square_mirror(square)
                mg_pst = mg_table[mirror_square]
                eg_pst = eg_table[mirror_square]

                # Subtract from scores (Black wants negative)
                mg_score -= (mg_material + mg_pst)
                eg_score -= (eg_material + eg_pst)

        # TAPER: Blend MG and EG scores based on game phase
        # Formula: (mg_score * phase + eg_score * (24 - phase)) / 24
        # When phase=24 (opening): 100% mg_score
        # When phase=0 (endgame): 100% eg_score
        total_score = (mg_score * game_phase + eg_score * (24 - game_phase)) / 24

        # TEMPO BONUS: Small bonus for side to move (standard in modern engines)
        # This reflects the initiative advantage of having the move
        TEMPO_BONUS = 10
        if board.turn == chess.WHITE:
            total_score += TEMPO_BONUS
        else:
            total_score -= TEMPO_BONUS

        return int(total_score)


    def select_move(self, board, time_limit=45.0, target_depth=None, endgame_time_limit=5.0):
        """
        Hybrid search policy:
        - Middlegame (phase > 12): fixed depth 5, fast and consistent moves
        - Endgame (phase <= 12): time-limited iterative deepening
          * Minimum depth 5 guaranteed (will exceed time limit if needed)
          * Can search deeper (depth 6+) if time permits within endgame_time_limit
          * Only uses completed depths (partial searches are discarded)

        Args:
            board: Current position
            time_limit: Time limit for general use (not used in hybrid mode)
            target_depth: Optional depth target (legacy parameter)
            endgame_time_limit: Time limit for endgame positions (default: 5 seconds)
        """

        # NOTE: TT is preserved across moves for better performance
        # Only clear TT at the start of a new game, not between moves
        # This allows reuse of opponent response analysis and PV persistence

        gc.disable()
        start_time = time.time()

        best_move = None
        best_value = None

        # --- TUNABLES ---
        MIDGAME_FIXED_DEPTH = 5
        ENDGAME_PHASE_THRESHOLD = 12  # phase <= this => endgame time mode (matches MG/EG display)
        ENDGAME_MIN_DEPTH = 5         # minimum depth to complete in endgame
        ENDGAME_MAX_DEPTH = 99        # practical cap for iterative deepening in endgames

        try:
            # Decide mode based on phase (0=endgame, 24=opening)
            # This matches the display logic: phase > 12 shows "MG", phase <= 12 shows "EG"
            phase = self.calculate_game_phase(board)

            if phase > ENDGAME_PHASE_THRESHOLD:
                # MIDGAME/OPENING: fixed depth, no time checks
                mode = "fixed"
                max_depth = MIDGAME_FIXED_DEPTH
                hard_time_limit = None
                min_depth = None
            else:
                # ENDGAME: time-limited iterative deepening (allows deeper search)
                mode = "timed"
                max_depth = ENDGAME_MAX_DEPTH
                hard_time_limit = endgame_time_limit  # Use dedicated endgame time limit
                min_depth = ENDGAME_MIN_DEPTH  # Must complete at least depth 5

            # Iterative deepening loop
            for current_depth in range(1, max_depth + 1):

                # Time check only in timed mode (endgames), but not before minimum depth
                if hard_time_limit is not None and (time.time() - start_time) >= hard_time_limit:
                    # If we haven't reached minimum depth yet, keep going
                    if min_depth is not None and current_depth <= min_depth:
                        print(f"  ⏱ Time limit reached, but continuing to minimum depth {min_depth}...")
                    else:
                        print(f"\n⏱ Time limit reached. Stopping at depth {current_depth - 1}")
                        break

                elapsed = time.time() - start_time

                # Reset performance counters for this depth
                depth_start_time = time.time()
                self.nodes_searched = 0
                self.tt_hits = 0
                self.tt_misses = 0
                self.tt_cutoffs = 0
                self.alpha_cutoffs = 0
                self.quiescence_nodes = 0

                print(f"\n📊 Depth {current_depth} (Elapsed: {elapsed:.1f}s) | Mode: {mode.upper()} | Phase: {phase}/24")

                # Get all legal moves
                legal_moves = list(board.legal_moves)
                if not legal_moves:
                    return None

                # MOVE ORDERING: TT best move first (from previous searches)
                board_hash = chess.polyglot.zobrist_hash(board)
                if board_hash in self.transposition_table:
                    tt_best_move = self.transposition_table[board_hash].get('best_move')
                    if tt_best_move and tt_best_move in legal_moves:
                        legal_moves.remove(tt_best_move)
                        legal_moves.insert(0, tt_best_move)

                # Sort remaining moves by MVV-LVA + killer + history scoring
                if len(legal_moves) > 1:
                    legal_moves = [legal_moves[0]] + sorted(
                        legal_moves[1:],
                        key=lambda m: self.score_move(board, m, ply=0),
                        reverse=True
                    )

                # ASPIRATION WINDOWS: Use narrow window around previous score from depth 2+
                # This speeds up search 20-40% when evals are stable
                ASPIRATION_WINDOW = 50
                if current_depth >= 2 and best_value is not None:
                    # Start with narrow window around previous depth's score
                    alpha = best_value - ASPIRATION_WINDOW
                    beta = best_value + ASPIRATION_WINDOW
                    use_aspiration = True
                else:
                    # Full window for depth 1 or no previous score
                    alpha = -100000
                    beta = 100000
                    use_aspiration = False

                # Save original bounds for fail detection (alpha/beta get modified during search)
                alpha_original = alpha
                beta_original = beta

                depth_best_move = None
                depth_best_value = -999999 if board.turn == chess.WHITE else 999999

                moves_searched = 0
                total_moves = len(legal_moves)
                research_needed = False

                # Search all moves at this depth
                for move in legal_moves:
                    # Time check only in timed mode (but not before minimum depth)
                    if hard_time_limit is not None and (time.time() - start_time) >= hard_time_limit:
                        # If we haven't reached minimum depth yet, keep going
                        if min_depth is None or current_depth > min_depth:
                            print(f"⏱ Time limit reached during depth {current_depth} ({moves_searched}/{total_moves} moves searched, {moves_searched/total_moves*100:.1f}%)")
                            break

                    moves_searched += 1

                    board.push(move)
                    move_value = self.minimax(board, current_depth - 1, alpha, beta, 0)
                    board.pop()

                    # Update best move for this depth
                    if board.turn == chess.WHITE:
                        if move_value > depth_best_value:
                            depth_best_value = move_value
                            depth_best_move = move
                        alpha = max(alpha, depth_best_value)
                    else:
                        if move_value < depth_best_value:
                            depth_best_value = move_value
                            depth_best_move = move
                        beta = min(beta, depth_best_value)

                # ASPIRATION WINDOW FAIL HANDLING
                completed = (moves_searched >= total_moves)
                if completed and use_aspiration:
                    # Check if we failed high or low using ORIGINAL bounds (not modified alpha/beta)
                    if depth_best_value <= alpha_original:  # Fail low
                        print(f"  ⚠ Aspiration fail-low (score {depth_best_value:+d} <= {alpha_original:+d}), re-searching with full window...")
                        research_needed = True
                    elif depth_best_value >= beta_original:  # Fail high
                        print(f"  ⚠ Aspiration fail-high (score {depth_best_value:+d} >= {beta_original:+d}), re-searching with full window...")
                        research_needed = True

                    # Re-search with full window if needed
                    if research_needed:
                        alpha = -100000
                        beta = 100000
                        moves_searched = 0
                        depth_best_value = -999999 if board.turn == chess.WHITE else 999999

                        for move in legal_moves:
                            moves_searched += 1
                            board.push(move)
                            move_value = self.minimax(board, current_depth - 1, alpha, beta, 0)
                            board.pop()

                            if board.turn == chess.WHITE:
                                if move_value > depth_best_value:
                                    depth_best_value = move_value
                                    depth_best_move = move
                                alpha = max(alpha, depth_best_value)
                            else:
                                if move_value < depth_best_value:
                                    depth_best_value = move_value
                                    depth_best_move = move
                                beta = min(beta, depth_best_value)

                        completed = (moves_searched >= total_moves)
                        print(f"  ✓ Re-search complete | New score: {depth_best_value:+d}")

                # Stats
                depth_time = time.time() - depth_start_time
                total_nodes = self.nodes_searched
                nps = int(total_nodes / depth_time) if depth_time > 0 else 0
                tt_hit_rate = (self.tt_hits / (self.tt_hits + self.tt_misses) * 100) if (self.tt_hits + self.tt_misses) > 0 else 0

                # In FIXED mode we *expect* completion; if it doesn't complete, something exploded (usually QS).
                if mode == "fixed" and not completed:
                    print(f"  ❌ FIXED DEPTH DID NOT COMPLETE ({moves_searched}/{total_moves}).")
                    print(f"  💾 Falling back to last completed: {best_move} | Score: {best_value if best_value is not None else 0:+d}")
                    print(f"  ⏱ Time: {depth_time:.2f}s | Nodes: {total_nodes:,} | Speed: {nps:,} nps")
                    break

                # Update best only if completed
                if depth_best_move and completed:
                    best_move = depth_best_move
                    best_value = depth_best_value

                    print(f"  ✓ COMPLETE | Best: {best_move} | Score: {best_value:+d}")
                    print(f"  ⏱ Time: {depth_time:.2f}s | Nodes: {total_nodes:,} | Speed: {nps:,} nodes/sec")
                    print(f"  🗃 TT hits: {self.tt_hits:,} ({tt_hit_rate:.1f}%) | Cutoffs: {self.tt_cutoffs:,}")
                    print(f"  ✂️ Alpha-beta cutoffs: {self.alpha_cutoffs:,}")
                    print(f"  🎯 Quiescence nodes: {self.quiescence_nodes:,} ({(self.quiescence_nodes/total_nodes*100):.1f}% of total)" if total_nodes > 0 else "  🎯 Quiescence nodes: 0")

                    # EARLY EXIT: If we found a forced mate, play it immediately (no need to search deeper)
                    if best_value is not None and abs(best_value) >= 90000:
                        mate_in = (100000 - abs(best_value) + 1) // 2  # Approximate mate distance
                        print(f"  ✨ Mate found (Mate in ~{mate_in})! Stopping search to play immediately.")
                        break
                else:
                    # Partial search (only possible in timed mode)
                    print(f"  ⚠ PARTIAL ({moves_searched}/{total_moves}) | Found: {depth_best_move} (score: {depth_best_value:+d}) - DISCARDED")
                    print(f"  💾 Using depth {current_depth-1} result: {best_move} | Score: {best_value if best_value is not None else 0:+d}")
                    print(f"  ⏱ Time: {depth_time:.2f}s | Nodes: {total_nodes:,}")

                # Stop conditions
                if mode == "fixed":
                    if current_depth >= MIDGAME_FIXED_DEPTH:
                        print(f"\n🎯 Fixed depth {MIDGAME_FIXED_DEPTH} reached. Stopping search.")
                        break
                else:
                    # timed mode: check if we've met minimum depth requirement
                    if completed and current_depth >= ENDGAME_MIN_DEPTH:
                        # Optional: continue to target depth if specified
                        if target_depth and current_depth >= target_depth:
                            print(f"\n🎯 Target depth {target_depth} reached (minimum {ENDGAME_MIN_DEPTH} satisfied). Stopping search.")
                            break

            # Optional debug info about chosen move (same style as your original)
            if best_move:
                phase_now = self.calculate_game_phase(board)
                piece = board.piece_at(best_move.from_square)

                if piece:
                    if piece.piece_type == chess.PAWN: mg_table, eg_table = PAWN_MG, PAWN_EG
                    elif piece.piece_type == chess.KNIGHT: mg_table, eg_table = KNIGHT_MG, KNIGHT_EG
                    elif piece.piece_type == chess.BISHOP: mg_table, eg_table = BISHOP_MG, BISHOP_EG
                    elif piece.piece_type == chess.ROOK: mg_table, eg_table = ROOK_MG, ROOK_EG
                    elif piece.piece_type == chess.QUEEN: mg_table, eg_table = QUEEN_MG, QUEEN_EG
                    elif piece.piece_type == chess.KING: mg_table, eg_table = KING_MG, KING_EG
                    else: mg_table, eg_table = [0]*64, [0]*64

                    def get_tapered_pst(square, color):
                        sq = square if color == chess.WHITE else chess.square_mirror(square)
                        return (mg_table[sq] * phase_now + eg_table[sq] * (24 - phase_now)) / 24

                    val_start = get_tapered_pst(best_move.from_square, piece.color)
                    val_end = get_tapered_pst(best_move.to_square, piece.color)
                    diff = val_end - val_start

                    print(f"   L-> Phase: {phase_now}/24 ({'MG' if phase_now > 12 else 'EG'}) | Piece: {chess.piece_name(piece.piece_type)}")
                    print(f"   L-> Tapered PST: {val_start:.1f} -> {val_end:.1f} ({'+' if diff >= 0 else ''}{diff:.1f})")

            # Return both move and score (score may be None if no move found)
            return (best_move, best_value)

        finally:
            gc.enable()


    # Worker to recursively look down the tree
    # This must be at the same indentation level as select_move!
    def minimax(self, board, depth, alpha, beta, ply_from_root=0):
        # CRITICAL: Check for draws FIRST to prevent shuffling into repetitions
        # Only check after root (ply_from_root > 0) since root position can't be a repetition yet
        if ply_from_root > 0 and (board.is_repetition(2) or board.can_claim_draw()):
            return 0  # Draw is worth 0

        # Derive maximizing/minimizing from side to move
        is_maximizing = (board.turn == chess.WHITE)

        # BASE CASE: if the game ended (don't treat claimable draw as forced terminal)
        if board.is_game_over(claim_draw=False):
            self.nodes_searched += 1  # Count terminal nodes
            return self.evaluate_board(board, ply_from_root)

        # BASE CASE: if we hit our depth limit, enter quiescence search
        # Quiescence will count its own nodes, so don't count here (avoid double-counting)
        if depth == 0:
            return self.quiescence(board, alpha, beta, ply_from_root)

        # Count this internal minimax node (after base cases to avoid double-counting)
        self.nodes_searched += 1

        # SAVE TRUE ORIGINAL BOUNDS (must be BEFORE TT probe which may tighten them)
        alpha_orig = alpha
        beta_orig = beta

        # TRANSPOSITION TABLE LOOKUP
        # Check if we've already evaluated this position
        # IMPORTANT: Skip TT cutoffs at root (ply_from_root=0) to ensure repetition detection works
        board_hash = chess.polyglot.zobrist_hash(board)
        if ply_from_root > 0 and board_hash in self.transposition_table:
            self.tt_hits += 1
            entry = self.transposition_table[board_hash]
            # Only use the entry if it was searched to sufficient depth
            if entry['depth'] >= depth:
                flag = entry['flag']
                tt_score = entry['score']

                # DE-NORMALIZE mate scores: Convert position-relative to root-relative
                # TT stores "mate-in-N from this position", we need "mate at ply X from root"
                # Formula: score = stored - ply_from_root (makes distant mates worth LESS)
                if tt_score > 90000:  # White mate
                    tt_score -= ply_from_root
                elif tt_score < -90000:  # Black mate
                    tt_score += ply_from_root

                # Check if we can use this score based on the flag
                if flag == TT_EXACT:
                    self.tt_cutoffs += 1
                    return tt_score  # Exact score, use it!
                elif flag == TT_LOWERBOUND:
                    # This position is AT LEAST this good
                    alpha = max(alpha, tt_score)
                elif flag == TT_UPPERBOUND:
                    # This position is AT MOST this good
                    beta = min(beta, tt_score)

                # If alpha >= beta after TT update, we have a cutoff
                if alpha >= beta:
                    self.tt_cutoffs += 1
                    # Return the bound that caused the cutoff, not necessarily tt_score
                    return alpha if flag == TT_LOWERBOUND else beta
        else:
            self.tt_misses += 1

        # RECURSIVE STEP
        best_move = None

        if is_maximizing:
            # It's White's turn in simulation, White tries to maximize score
            max_eval = -999999

            # MOVE ORDERING: TT best move first, then killers, then MVV-LVA + history
            moves = list(board.legal_moves)
            tt_move = None

            # Check if TT has a best move for this position
            if board_hash in self.transposition_table:
                tt_move = self.transposition_table[board_hash].get('best_move')
                if tt_move and tt_move in moves:
                    # Put TT move first
                    moves.remove(tt_move)
                    moves.insert(0, tt_move)

            # Sort remaining moves by score (MVV-LVA + killers + history)
            if tt_move and len(moves) > 1:
                moves = [moves[0]] + sorted(moves[1:], key=lambda m: self.score_move(board, m, ply_from_root), reverse=True)
            else:
                moves = sorted(moves, key=lambda m: self.score_move(board, m, ply_from_root), reverse=True)
            for move in moves:
                board.push(move)

                # Pass alpha/beta down
                # recursion. now it's Black's turn (will be derived as is_maximizing = False)
                eval = self.minimax(board, depth - 1, alpha, beta, ply_from_root + 1)
                board.pop()

                # Track best move
                if eval > max_eval:
                    max_eval = eval
                    best_move = move

                # Pruning logic
                alpha = max(alpha, eval) # 1. Update Alpha
                if beta <= alpha:        # 2. Check for cut-off
                    self.alpha_cutoffs += 1

                    # Update killer moves and history for quiet moves that caused beta cutoff
                    if not board.is_capture(move) and not move.promotion:
                        # Update history table (depth-squared bonus)
                        self.history_table[move.from_square][move.to_square] += depth * depth

                        # Update killer moves for this ply (keep most recent 2)
                        if ply_from_root < len(self.killer_moves):
                            if move != self.killer_moves[ply_from_root][0]:
                                # Shift: new move becomes primary, old primary becomes secondary
                                self.killer_moves[ply_from_root][1] = self.killer_moves[ply_from_root][0]
                                self.killer_moves[ply_from_root][0] = move

                    break                # 3. Stop searching this branch

            # STORE IN TRANSPOSITION TABLE
            # Determine what type of score this is using TRUE original bounds
            if max_eval <= alpha_orig:
                flag = TT_UPPERBOUND  # Fail-low: true score <= this
            elif max_eval >= beta_orig:
                flag = TT_LOWERBOUND  # Fail-high: true score >= this
            else:
                flag = TT_EXACT  # We searched all moves fully

            # NORMALIZE mate scores before storing: Convert root-relative to position-relative
            # evaluate_board returns root-relative scores (100000 - ply_from_root)
            # We convert to position-relative so TT is path-independent
            # Formula: stored = score + ply_from_root (encodes "mate-in-N from this position")
            stored_score = max_eval
            if stored_score > 90000:  # White mate
                stored_score += ply_from_root
            elif stored_score < -90000:  # Black mate
                stored_score -= ply_from_root

            # TT REPLACEMENT POLICY: Depth-preferred with EXACT priority
            should_replace = True
            if board_hash in self.transposition_table:
                old_entry = self.transposition_table[board_hash]
                old_depth = old_entry['depth']
                old_flag = old_entry['flag']

                # Keep deeper entries unless new entry is better quality
                if old_depth > depth:
                    # Only replace deeper entry if new is EXACT and old is bound
                    should_replace = (flag == TT_EXACT and old_flag != TT_EXACT)
                # If equal depth, only replace if new is EXACT and old isn't (reduce churn)
                elif old_depth == depth:
                    should_replace = (flag == TT_EXACT and old_flag != TT_EXACT)
                # If new is deeper, always replace
                # (should_replace stays True)

            if should_replace:
                self.transposition_table[board_hash] = {
                    'score': stored_score,
                    'depth': depth,
                    'flag': flag,
                    'best_move': best_move
                }

            return max_eval
        else:
            # It's Black's turn. Black tries to minimize score
            min_eval = 999999

            # MOVE ORDERING: TT best move first, then killers, then MVV-LVA + history
            moves = list(board.legal_moves)
            tt_move = None

            # Check if TT has a best move for this position
            if board_hash in self.transposition_table:
                tt_move = self.transposition_table[board_hash].get('best_move')
                if tt_move and tt_move in moves:
                    # Put TT move first
                    moves.remove(tt_move)
                    moves.insert(0, tt_move)

            # Sort remaining moves by score (MVV-LVA + killers + history)
            if tt_move and len(moves) > 1:
                moves = [moves[0]] + sorted(moves[1:], key=lambda m: self.score_move(board, m, ply_from_root), reverse=True)
            else:
                moves = sorted(moves, key=lambda m: self.score_move(board, m, ply_from_root), reverse=True)
            for move in moves:
                board.push(move)
                # recursion. now it's white's turn (is_maximizing = True)
                eval = self.minimax(board, depth - 1, alpha, beta, ply_from_root + 1)
                board.pop()

                # Track best move
                if eval < min_eval:
                    min_eval = eval
                    best_move = move

                # Pruning Logic
                beta = min(beta, eval) # 1. Update Beta
                if beta <= alpha:      # 2. Check for cut-off
                    self.alpha_cutoffs += 1

                    # Update killer moves and history for quiet moves that caused beta cutoff
                    if not board.is_capture(move) and not move.promotion:
                        # Update history table (depth-squared bonus)
                        self.history_table[move.from_square][move.to_square] += depth * depth

                        # Update killer moves for this ply (keep most recent 2)
                        if ply_from_root < len(self.killer_moves):
                            if move != self.killer_moves[ply_from_root][0]:
                                # Shift: new move becomes primary, old primary becomes secondary
                                self.killer_moves[ply_from_root][1] = self.killer_moves[ply_from_root][0]
                                self.killer_moves[ply_from_root][0] = move

                    break              # 3. Stop searching this branch

            # STORE IN TRANSPOSITION TABLE
            # Determine what type of score this is using TRUE original bounds
            if min_eval <= alpha_orig:
                flag = TT_UPPERBOUND  # Fail-low: true score <= this
            elif min_eval >= beta_orig:
                flag = TT_LOWERBOUND  # Fail-high: true score >= this
            else:
                flag = TT_EXACT  # We searched all moves fully

            # NORMALIZE mate scores before storing: Convert root-relative to position-relative
            # evaluate_board returns root-relative scores (100000 - ply_from_root)
            # We convert to position-relative so TT is path-independent
            # Formula: stored = score + ply_from_root (encodes "mate-in-N from this position")
            stored_score = min_eval
            if stored_score > 90000:  # White mate
                stored_score += ply_from_root
            elif stored_score < -90000:  # Black mate
                stored_score -= ply_from_root

            # TT REPLACEMENT POLICY: Depth-preferred with EXACT priority
            should_replace = True
            if board_hash in self.transposition_table:
                old_entry = self.transposition_table[board_hash]
                old_depth = old_entry['depth']
                old_flag = old_entry['flag']

                # Keep deeper entries unless new entry is better quality
                if old_depth > depth:
                    # Only replace deeper entry if new is EXACT and old is bound
                    should_replace = (flag == TT_EXACT and old_flag != TT_EXACT)
                # If equal depth, only replace if new is EXACT and old isn't (reduce churn)
                elif old_depth == depth:
                    should_replace = (flag == TT_EXACT and old_flag != TT_EXACT)
                # If new is deeper, always replace
                # (should_replace stays True)

            if should_replace:
                self.transposition_table[board_hash] = {
                    'score': stored_score,
                    'depth': depth,
                    'flag': flag,
                    'best_move': best_move
                }

            return min_eval

    # Quiescence Search: Search only tactical moves until position is "quiet"
    # This prevents horizon effect bugs where we evaluate mid-capture
    def quiescence(self, board, alpha, beta, ply_from_root=0, qs_depth=0, max_qs_depth=16):
        """
        Search only tactical moves (captures and promotions) until quiet.

        This prevents the horizon effect where the bot stops searching
        in the middle of a forcing sequence and misjudges the position.

        Implements both delta pruning and depth limiting (gold standard):
        - Delta pruning: Skip hopeless non-promotion captures (margin 100cp, not when in check)
        - Depth limit: Safety net to prevent quiescence explosion (cap at 16 plies)

        Args:
            board: Current position
            alpha, beta: Alpha-beta bounds
            ply_from_root: Distance from root (for mate distance scoring)
            qs_depth: Current quiescence search depth (separate from ply_from_root)
            max_qs_depth: Maximum quiescence depth to prevent explosions (default: 16)

        Returns:
            Static evaluation after searching tactical sequences
        """
        # Count all nodes (including quiescence)
        self.nodes_searched += 1
        self.quiescence_nodes += 1

        # SPLIT DEPTH CAPS: Stricter limit when in check to prevent check-chase spirals
        # In-check QS can branch hard (all evasions), so use tighter cap
        if board.is_check():
            cap = 6   # In-check cap (try 6 first, can tighten to 5 if needed)
        else:
            cap = 12  # Normal QS cap (try 12 first, can tighten to 10 if needed)

        # SAFETY: Prevent quiescence explosion
        if qs_depth >= cap:
            return self.evaluate_board(board, ply_from_root)

        # Check for terminal positions first (don't force claimable draws as terminal)
        if board.is_game_over(claim_draw=False):
            return self.evaluate_board(board, ply_from_root)

        # Check if we're in check (affects stand-pat and move generation)
        in_check = board.is_check()

        # Calculate game phase once (for delta pruning decision)
        phase = self.calculate_game_phase(board)

        # STAND PAT: Evaluate the current position as our baseline
        # IMPORTANT: Only if NOT in check (when in check, we MUST move)
        stand_pat = self.evaluate_board(board, ply_from_root)

        # Determine if we're maximizing or minimizing
        is_maximizing = (board.turn == chess.WHITE)

        if is_maximizing:
            # WHITE (maximizing player)

            # Beta cutoff: if standing pat is already too good, opponent won't let us get here
            # But ONLY if not in check (when in check, we can't "stand pat")
            if not in_check:
                if stand_pat >= beta:
                    return beta

                # Update alpha with stand-pat (our baseline guarantee)
                if stand_pat > alpha:
                    alpha = stand_pat

            # MOVE GENERATION: Special case when in check (must search all evasions)
            if in_check:
                # When in check, search ALL legal moves (evasions), not just captures
                tactical_moves = list(board.legal_moves)
            else:
                # Normal QS: captures and promotions only (NO checks to prevent explosion)
                tactical_moves = [m for m in board.legal_moves if board.is_capture(m) or m.promotion]

            # If no tactical moves, position is quiet - return stand-pat
            if not tactical_moves:
                return stand_pat

            # Order tactical moves for better pruning (pass ply for killer/history)
            tactical_moves.sort(key=lambda m: self.score_move(board, m, ply_from_root), reverse=True)

            # Search tactical moves with LAZY DELTA PRUNING (safe version)
            for move in tactical_moves:
                # DELTA PRUNING: Skip hopeless non-promotion captures
                # Safe conditions: NOT in check, NOT in endgame (phase > 4), NOT a promotion
                # Note: phase is calculated once outside the loop for efficiency
                if board.is_capture(move) and not move.promotion and not in_check and phase > 4:
                    victim_type = board.piece_type_at(move.to_square)
                    if not victim_type and board.is_en_passant(move):
                        victim_type = chess.PAWN

                    if victim_type:
                        victim_value = self.piece_values[victim_type]
                        # If even capturing + 100cp margin can't beat alpha, skip it
                        if stand_pat + victim_value + 100 < alpha:
                            continue

                board.push(move)
                score = self.quiescence(board, alpha, beta, ply_from_root + 1, qs_depth + 1, max_qs_depth)
                board.pop()

                if score >= beta:
                    return beta  # Beta cutoff

                if score > alpha:
                    alpha = score

            return alpha

        else:
            # BLACK (minimizing player)

            # Alpha cutoff: if standing pat is already too good for us, opponent won't let us get here
            # But ONLY if not in check (when in check, we can't "stand pat")
            if not in_check:
                if stand_pat <= alpha:
                    return alpha

                # Update beta with stand-pat (our baseline guarantee)
                if stand_pat < beta:
                    beta = stand_pat

            # MOVE GENERATION: Special case when in check (must search all evasions)
            if in_check:
                # When in check, search ALL legal moves (evasions), not just captures
                tactical_moves = list(board.legal_moves)
            else:
                # Normal QS: captures and promotions only (NO checks to prevent explosion)
                tactical_moves = [m for m in board.legal_moves if board.is_capture(m) or m.promotion]

            # If no tactical moves, position is quiet - return stand-pat
            if not tactical_moves:
                return stand_pat

            # Order tactical moves for better pruning (pass ply for killer/history)
            tactical_moves.sort(key=lambda m: self.score_move(board, m, ply_from_root), reverse=True)

            # Search tactical moves with LAZY DELTA PRUNING (safe version)
            for move in tactical_moves:
                # DELTA PRUNING: Skip hopeless non-promotion captures
                # Safe conditions: NOT in check, NOT in endgame (phase > 4), NOT a promotion
                # Note: phase is calculated once outside the loop for efficiency
                if board.is_capture(move) and not move.promotion and not in_check and phase > 4:
                    victim_type = board.piece_type_at(move.to_square)
                    if not victim_type and board.is_en_passant(move):
                        victim_type = chess.PAWN

                    if victim_type:
                        victim_value = self.piece_values[victim_type]
                        # If even capturing + 100cp margin can't beat beta, skip it
                        if stand_pat - victim_value - 100 > beta:
                            continue

                board.push(move)
                score = self.quiescence(board, alpha, beta, ply_from_root + 1, qs_depth + 1, max_qs_depth)
                board.pop()

                if score <= alpha:
                    return alpha  # Alpha cutoff

                if score < beta:
                    beta = score

            return beta