// ============================================================================
// PestoPasta C++ Chess Engine
// UCI-compatible chess engine using chess-library (bitboards + magic bitboards)
//
// Compile: g++ -O3 -std=c++17 -I./chess-library/include -o pasta_engine pasta_engine.cpp
// Usage: ./pasta_engine (then type UCI commands)
// ============================================================================

#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>
#include <chrono>
#include <limits>
#include <cstdint>
#include "chess.hpp"

using namespace chess;

// ============================================================================
// PESTO EVALUATION TABLES (Centipawns)
// ============================================================================

// Piece values (middlegame and endgame)
const int PIECE_VALUES_MG[] = {82, 337, 365, 477, 1025, 0};  // P N B R Q K
const int PIECE_VALUES_EG[] = {94, 281, 297, 512, 936, 0};

// PeSTO Piece-Square Tables (from White's perspective, rank-1-first, a1=0, h8=63)
// Indices 0-7 = rank 1, 8-15 = rank 2, ..., 56-63 = rank 8
const int PAWN_MG[64] = {
    0,   0,   0,   0,   0,   0,  0,   0,
    -35,  -1, -20, -23, -15,  24, 38, -22,
    -26,  -4,  -4, -10,   3,   3, 33, -12,
    -27,  -2,  -5,  12,  17,   6, 10, -25,
    -14,  13,   6,  21,  23,  12, 17, -23,
     -6,   7,  26,  31,  65,  56, 25, -20,
     98, 134,  61,  95,  68, 126, 34, -11,
      0,   0,   0,   0,   0,   0,  0,   0,
};

const int PAWN_EG[64] = {
      0,   0,   0,   0,   0,   0,   0,   0,
     13,   8,   8,  10,  13,   0,   2,  -7,
      4,   7,  -6,   1,   0,  -5,  -1,  -8,
     13,   9,  -3,  -7,  -7,  -8,   3,  -1,
     32,  24,  13,   5,  -2,   4,  17,  17,
     94, 100,  85,  67,  56,  53,  82,  84,
    178, 173, 158, 134, 147, 132, 165, 187,
      0,   0,   0,   0,   0,   0,   0,   0,
};

const int KNIGHT_MG[64] = {
    -105, -21, -58, -33, -17, -28, -19,  -23,
     -29, -53, -12,  -3,  -1,  18, -14,  -19,
     -23,  -9,  12,  10,  19,  17,  25,  -16,
     -13,   4,  16,  13,  28,  19,  21,   -8,
      -9,  17,  19,  53,  37,  69,  18,   22,
     -47,  60,  37,  65,  84, 129,  73,   44,
     -73, -41,  72,  36,  23,  62,   7,  -17,
    -167, -89, -34, -49,  61, -97, -15, -107,
};

const int KNIGHT_EG[64] = {
    -29, -51, -23, -15, -22, -18, -50, -64,
    -42, -20, -10,  -5,  -2, -20, -23, -44,
    -23,  -3,  -1,  15,  10,  -3, -20, -22,
    -18,  -6,  16,  25,  16,  17,   4, -18,
    -17,   3,  22,  22,  22,  11,   8, -18,
    -24, -20,  10,   9,  -1,  -9, -19, -41,
    -25,  -8, -25,  -2,  -9, -25, -24, -52,
    -58, -38, -13, -28, -31, -27, -63, -99,
};

const int BISHOP_MG[64] = {
    -33,  -3, -14, -21, -13, -12, -39, -21,
      4,  15,  16,   0,   7,  21,  33,   1,
      0,  15,  15,  15,  14,  27,  18,  10,
     -6,  13,  13,  26,  34,  12,  10,   4,
     -4,   5,  19,  50,  37,  37,   7,  -2,
    -16,  37,  43,  40,  35,  50,  37,  -2,
    -26,  16, -18, -13,  30,  59,  18, -47,
    -29,   4, -82, -37, -25, -42,   7,  -8,
};

const int BISHOP_EG[64] = {
    -23,  -9, -23,  -5, -9, -16,  -5, -17,
    -14, -18,  -7,  -1,  4,  -9, -15, -27,
    -12,  -3,   8,  10, 13,   3,  -7, -15,
     -6,   3,  13,  19,  7,  10,  -3,  -9,
     -3,   9,  12,   9, 14,  10,   3,   2,
      2,  -8,   0,  -1, -2,   6,   0,   4,
     -8,  -4,   7, -12, -3, -13,  -4, -14,
    -14, -21, -11,  -8, -7,  -9, -17, -24,
};

const int ROOK_MG[64] = {
    -19, -13,   1,  17, 16,  7, -37, -26,
    -44, -16, -20,  -9, -1, 11,  -6, -71,
    -45, -25, -16, -17,  3,  0,  -5, -33,
    -36, -26, -12,  -1,  9, -7,   6, -23,
    -24, -11,   7,  26, 24, 35,  -8, -20,
     -5,  19,  26,  36, 17, 45,  61,  16,
     27,  32,  58,  62, 80, 67,  26,  44,
     32,  42,  32,  51, 63,  9,  31,  43,
};

const int ROOK_EG[64] = {
    -9,  2,  3, -1, -5, -13,   4, -20,
    -6, -6,  0,  2, -9,  -9, -11,  -3,
    -4,  0, -5, -1, -7, -12,  -8, -16,
     3,  5,  8,  4, -5,  -6,  -8, -11,
     4,  3, 13,  1,  2,   1,  -1,   2,
     7,  7,  7,  5,  4,  -3,  -5,  -3,
    11, 13, 13, 11, -3,   3,   8,   3,
    13, 10, 18, 15, 12,  12,   8,   5,
};

const int QUEEN_MG[64] = {
     -1, -18,  -9,  10, -15, -25, -31, -50,
    -35,  -8,  11,   2,   8,  15,  -3,   1,
    -14,   2, -11,  -2,  -5,   2,  14,   5,
     -9, -26,  -9, -10,  -2,  -4,   3,  -3,
    -27, -27, -16, -16,  -1,  17,  -2,   1,
    -13, -17,   7,   8,  29,  56,  47,  57,
    -24, -39,  -5,   1, -16,  57,  28,  54,
    -28,   0,  29,  12,  59,  44,  43,  45,
};

const int QUEEN_EG[64] = {
    -33, -28, -22, -43,  -5, -32, -20, -41,
    -22, -23, -30, -16, -16, -23, -36, -32,
    -16, -27,  15,   6,   9,  17,  10,   5,
    -18,  28,  19,  47,  31,  34,  39,  23,
      3,  22,  24,  45,  57,  40,  57,  36,
    -20,   6,   9,  49,  47,  35,  19,   9,
    -17,  20,  32,  41,  58,  25,  30,   0,
     -9,  22,  22,  27,  27,  19,  10,  20,
};

const int KING_MG[64] = {
    -15,  36,  12, -54,   8, -28,  24,  14,
      1,   7,  -8, -64, -43, -16,   9,   8,
    -14, -14, -22, -46, -44, -30, -15, -27,
    -49,  -1, -27, -39, -46, -44, -33, -51,
    -17, -20, -12, -27, -30, -25, -14, -36,
     -9,  24,   2, -16, -20,   6,  22, -22,
     29,  -1, -20,  -7,  -8,  -4, -38, -29,
    -65,  23,  16, -15, -56, -34,   2,  13,
};

const int KING_EG[64] = {
    -53, -34, -21, -11, -28, -14, -24, -43,
    -27, -11,   4,  13,  14,   4,  -5, -17,
    -19,  -3,  11,  21,  23,  16,   7,  -9,
    -18,  -4,  21,  24,  27,  23,   9, -11,
     -8,  22,  24,  27,  26,  33,  26,   3,
     10,  17,  23,  15,  20,  45,  44,  13,
    -12,  17,  14,  17,  17,  38,  23,  11,
    -74, -35, -18, -18, -11,  15,   4, -17,
};

// PST arrays are already correctly oriented for a1=0 indexing (rank-1-first)
// Use them directly without flipping
const int* PST_MG[] = {PAWN_MG, KNIGHT_MG, BISHOP_MG, ROOK_MG, QUEEN_MG, KING_MG};
const int* PST_EG[] = {PAWN_EG, KNIGHT_EG, BISHOP_EG, ROOK_EG, QUEEN_EG, KING_EG};

// Helper to safely map PieceType to array indices (defensive against enum changes)
inline int pt_index(PieceType pt) {
    // For this library, PieceType values are 0-5 (Pawn=0, Knight=1, Bishop=2, Rook=3, Queen=4, King=5)
    // We cast to int for indexing, verified to be correct for chess-library
    return static_cast<int>(pt);
}

// ============================================================================
// TRANSPOSITION TABLE
// ============================================================================

const int TT_EXACT = 0;
const int TT_LOWERBOUND = 1;
const int TT_UPPERBOUND = 2;

struct TTEntry {
    uint64_t hash = 0;
    int score = 0;
    int depth = -1;  // -1 means empty slot
    int flag = 0;
    Move best_move = Move::NO_MOVE;
};

// ============================================================================
// ENGINE CLASS
// ============================================================================

// Fixed-size Transposition Table (32MB = ~1 million entries)
// More cache-friendly and predictable memory usage than unordered_map
// Conservative size for Koyeb's 256MB RAM limit (leaves room for stack + OS)
const size_t TT_SIZE = 1048576;  // 2^20 entries (~32MB with 32-byte entries)

class Engine {
public:
    Board board;
    std::vector<TTEntry> tt;
    Move killer_moves[128][2];
    int history_table[64][64];
    // Use same piece values as evaluation for consistency (PeSTO middlegame values)
    int piece_values[6] = {82, 337, 365, 477, 1025, 0};  // P N B R Q K

    // Performance stats
    int nodes_searched;
    int quiescence_nodes;
    int tt_hits, tt_misses, tt_cutoffs;
    int alpha_cutoffs;

    // Time management
    std::chrono::steady_clock::time_point search_start_time;
    int search_time_limit_ms;
    bool time_up;

    Engine() {
        tt.resize(TT_SIZE);
        clear_tables();
        search_time_limit_ms = 0;
        time_up = false;
    }

    // Check if we've exceeded our time limit (called periodically during search)
    inline bool check_time() {
        // Only check every 2048 nodes to minimize overhead (bitwise AND is faster than modulo)
        if (search_time_limit_ms > 0 && (nodes_searched & 2047) == 0) {
            auto now = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - search_start_time).count();
            if (elapsed >= search_time_limit_ms) {
                time_up = true;
                return true;
            }
        }
        return time_up;  // Always return current status
    }

    void clear_tables() {
        // Reset all TT entries to empty (depth = -1)
        for (size_t i = 0; i < TT_SIZE; i++) {
            tt[i].depth = -1;
        }
        for (int i = 0; i < 128; i++) {
            killer_moves[i][0] = killer_moves[i][1] = Move::NO_MOVE;
        }
        for (int i = 0; i < 64; i++) {
            for (int j = 0; j < 64; j++) {
                history_table[i][j] = 0;
            }
        }
    }

    // Probe TT with depth-preferred replacement
    TTEntry* probe_tt(uint64_t hash) {
        size_t index = hash % TT_SIZE;
        TTEntry* entry = &tt[index];

        // Check if entry is valid and matches hash
        if (entry->depth >= 0 && entry->hash == hash) {
            return entry;
        }
        return nullptr;
    }

    // Store in TT with depth-preferred replacement
    void store_tt(uint64_t hash, int score, int depth, int flag, Move best_move) {
        size_t index = hash % TT_SIZE;
        TTEntry* entry = &tt[index];

        // Replace if: empty slot OR same position OR deeper search
        if (entry->depth < 0 || entry->hash == hash || depth >= entry->depth) {
            entry->hash = hash;
            entry->score = score;
            entry->depth = depth;
            entry->flag = flag;
            entry->best_move = best_move;
        }
    }

    int calculate_phase(const Board& b) const {
        // Calculate game phase (0 = endgame, 24 = opening)
        int phase = 0;
        const int phase_values[] = {0, 1, 1, 2, 4, 0};  // P N B R Q K

        auto bb = b.occ();
        while (bb) {
            Square sq = bb.lsb();
            bb.pop();
            auto piece = b.at(sq);
            if (piece != Piece::NONE) {
                phase += phase_values[pt_index(piece.type())];
            }
        }
        return std::min(phase, 24);
    }

    int evaluate(const Board& b, int ply_from_root) {
        // Terminal states
        if (b.isGameOver().first != GameResultReason::NONE) {
            auto result = b.isGameOver();
            if (result.first == GameResultReason::CHECKMATE) {
                // Mate score: favor faster mates
                return (b.sideToMove() == Color::WHITE) ? -100000 + ply_from_root : 100000 - ply_from_root;
            }
            // Stalemate or draw
            return 0;
        }

        int phase = calculate_phase(b);
        int mg_score = 0, eg_score = 0;

        // Iterate through all pieces
        auto bb = b.occ();
        while (bb) {
            Square sq = bb.lsb();
            bb.pop();

            auto piece = b.at(sq);
            if (piece == Piece::NONE) continue;

            PieceType pt = piece.type();
            Color col = piece.color();

            int pt_idx = pt_index(pt);
            int mg_material = PIECE_VALUES_MG[pt_idx];
            int eg_material = PIECE_VALUES_EG[pt_idx];

            // Get PST value (rank flip for black)
            int sq_idx = sq.index();
            if (col == Color::BLACK) {
                sq_idx ^= 56;  // Flip ranks (a1 <-> a8, b1 <-> b8, etc.)
            }

            int mg_pst = PST_MG[pt_idx][sq_idx];
            int eg_pst = PST_EG[pt_idx][sq_idx];

            if (col == Color::WHITE) {
                mg_score += mg_material + mg_pst;
                eg_score += eg_material + eg_pst;
            } else {
                mg_score -= mg_material + mg_pst;
                eg_score -= eg_material + eg_pst;
            }
        }

        // Tapered evaluation
        int total = (mg_score * phase + eg_score * (24 - phase)) / 24;

        // Tempo bonus
        total += (b.sideToMove() == Color::WHITE) ? 10 : -10;

        return total;
    }

    int score_move(const Board& b, const Move& m, int ply) {
        auto from = m.from();
        auto to = m.to();
        auto captured = b.at(to);

        // MOVE ORDERING (highest to lowest priority):
        // 1. TT Move (handled in minimax loop)
        // 2. Promotions - 2,000,000+
        if (m.typeOf() == Move::PROMOTION) {
            return 2000000;
        }

        // 3. Captures (MVV-LVA) - 1,000,000 to 1,010,000
        // En passant is a special case - treat as pawn capturing pawn
        if (m.typeOf() == Move::ENPASSANT) {
            return 1000000 + (100 * 10) - 100;  // Pawn captures pawn
        }

        if (captured != Piece::NONE) {
            int victim_value = piece_values[pt_index(captured.type())];
            int attacker_value = piece_values[pt_index(b.at(from).type())];
            return 1000000 + (victim_value * 10) - attacker_value;
        }

        // 4. Killer moves (quiet moves) - 900,000 and 800,000
        if (m == killer_moves[ply][0]) return 900000;
        if (m == killer_moves[ply][1]) return 800000;

        // 5. History heuristic (quiet moves) - 0 to ~10,000
        return history_table[from.index()][to.index()];
    }

    int quiescence(Board& b, int alpha, int beta, int ply_from_root) {
        nodes_searched++;
        quiescence_nodes++;

        // Terminal check
        if (b.isGameOver().first != GameResultReason::NONE) {
            return evaluate(b, ply_from_root);
        }

        // Stand pat
        int stand_pat = evaluate(b, ply_from_root);
        bool in_check = b.inCheck();

        if (!in_check) {
            if (b.sideToMove() == Color::WHITE) {
                if (stand_pat >= beta) return beta;
                if (stand_pat > alpha) alpha = stand_pat;
            } else {
                if (stand_pat <= alpha) return alpha;
                if (stand_pat < beta) beta = stand_pat;
            }
        }

        // Generate moves based on check status
        // CRITICAL: When in check, we MUST search all legal evasions (not just captures)
        // This matches Python behavior and is required for correctness
        Movelist moves;
        if (in_check) {
            // In check: generate ALL legal evasions (king moves, blocks, captures)
            movegen::legalmoves(moves, b);

            // Check for checkmate
            if (moves.size() == 0) {
                return (b.sideToMove() == Color::WHITE) ? -100000 + ply_from_root : 100000 - ply_from_root;
            }
        } else {
            // Not in check: only generate captures (tactical search)
            movegen::legalmoves<movegen::MoveGenType::CAPTURE>(moves, b);
            if (moves.size() == 0) return stand_pat;
        }

        // Calculate game phase for delta pruning (same as Python)
        int phase = calculate_phase(b);

        // Sort moves
        std::vector<Move> sorted_moves;
        for (const auto& m : moves) {
            sorted_moves.push_back(m);
        }
        std::sort(sorted_moves.begin(), sorted_moves.end(), [&](const Move& move_a, const Move& move_b) {
            return score_move(b, move_a, ply_from_root) > score_move(b, move_b, ply_from_root);
        });

        // Search tactical moves with DELTA PRUNING
        for (const auto& m : sorted_moves) {
            // DELTA PRUNING: Skip hopeless non-promotion captures
            // Only when: NOT in check, NOT endgame (phase > 4), NOT promotion
            const int DELTA_MARGIN = 100;  // 100cp safety margin

            if (!in_check && phase > 4 && m.typeOf() != Move::PROMOTION) {
                int victim_value = 0;

                // Handle en passant specially (captured pawn is not at the "to" square)
                if (m.typeOf() == Move::ENPASSANT) {
                    victim_value = 100;  // Pawn
                } else {
                    auto captured = b.at(m.to());
                    if (captured != Piece::NONE) {
                        victim_value = piece_values[pt_index(captured.type())];
                    }
                }

                if (victim_value > 0) {
                    // Prune if even capturing + margin can't improve position
                    if (b.sideToMove() == Color::WHITE) {
                        if (stand_pat + victim_value + DELTA_MARGIN < alpha) {
                            continue;  // Skip this hopeless capture
                        }
                    } else {
                        // BLACK: optimistic bound still can't beat beta
                        if (stand_pat - victim_value + DELTA_MARGIN > beta) {
                            continue;  // Skip this hopeless capture
                        }
                    }
                }
            }

            b.makeMove(m);
            int score = quiescence(b, alpha, beta, ply_from_root + 1);
            b.unmakeMove(m);

            if (b.sideToMove() == Color::WHITE) {
                if (score >= beta) return beta;
                if (score > alpha) alpha = score;
            } else {
                if (score <= alpha) return alpha;
                if (score < beta) beta = score;
            }
        }

        return (b.sideToMove() == Color::WHITE) ? alpha : beta;
    }

    int minimax(Board& b, int depth, int alpha, int beta, int ply_from_root) {
        // Draw by repetition or 50-move rule
        // isRepetition(2) checks for 3-fold repetition (2 previous occurrences)
        if (b.isRepetition(2) || b.isHalfMoveDraw()) {
            return 0;
        }

        // Terminal check
        if (b.isGameOver().first != GameResultReason::NONE) {
            nodes_searched++;
            return evaluate(b, ply_from_root);
        }

        // Depth 0: enter quiescence
        if (depth == 0) {
            return quiescence(b, alpha, beta, ply_from_root);
        }

        nodes_searched++;

        int alpha_orig = alpha;
        int beta_orig = beta;

        // Transposition table lookup
        // Note: We use TT even at root (ply_from_root == 0) to reuse previous search
        uint64_t hash = b.hash();
        TTEntry* entry = probe_tt(hash);
        if (entry != nullptr && entry->depth >= depth) {
            tt_hits++;
            int tt_score = entry->score;

            // De-normalize mate scores
            if (tt_score > 90000) tt_score -= ply_from_root;
            else if (tt_score < -90000) tt_score += ply_from_root;

            if (entry->flag == TT_EXACT) {
                tt_cutoffs++;
                return tt_score;
            } else if (entry->flag == TT_LOWERBOUND) {
                alpha = std::max(alpha, tt_score);
            } else if (entry->flag == TT_UPPERBOUND) {
                beta = std::min(beta, tt_score);
            }

            if (alpha >= beta) {
                tt_cutoffs++;
                // In Minimax (not Negamax), return based on side to move:
                // White (maximizing) returns alpha, Black (minimizing) returns beta
                return (b.sideToMove() == Color::WHITE) ? alpha : beta;
            }
        } else {
            tt_misses++;
        }

        // NULL MOVE PRUNING: Try passing the turn and see if we still fail high/low
        // This is safe when: deep enough, not in check, not at root, have material
        if (depth >= 3 && !b.inCheck() && ply_from_root > 0) {
            // Only do NMP if we have non-pawn material (avoid zugzwang)
            bool has_material = false;
            auto our_color = b.sideToMove();
            auto occ = b.occ();

            while (occ) {
                auto sq = occ.lsb();
                auto piece = b.at(sq);
                if (piece != Piece::NONE && piece.color() == our_color &&
                    piece.type() != PieceType::PAWN && piece.type() != PieceType::KING) {
                    has_material = true;
                    break;
                }
                occ.pop();
            }

            if (has_material) {
                const int R = 2;  // Reduction factor (depth reduction)
                b.makeNullMove();
                // Use normal minimax call (handles side switching correctly)
                int null_score = minimax(b, depth - 1 - R, alpha, beta, ply_from_root + 1);
                b.unmakeNullMove();

                // Check for cutoff based on which side was originally to move
                if (our_color == Color::WHITE) {
                    // WHITE maximizes: if even after passing, score >= beta, position too good
                    if (null_score >= beta) {
                        return beta;
                    }
                } else {
                    // BLACK minimizes: if even after passing, score <= alpha, position too good for BLACK
                    if (null_score <= alpha) {
                        return alpha;
                    }
                }
            }
        }

        // Generate legal moves
        Movelist movelist;
        movegen::legalmoves(movelist, b);

        if (movelist.size() == 0) {
            // No legal moves (handled by isGameOver above, but double-check)
            return evaluate(b, ply_from_root);
        }

        // Move ordering
        std::vector<Move> moves;
        Move tt_move = Move::NO_MOVE;
        TTEntry* tt_entry = probe_tt(hash);
        if (tt_entry != nullptr) {
            tt_move = tt_entry->best_move;
        }

        for (const auto& m : movelist) {
            if (m == tt_move) {
                moves.insert(moves.begin(), m);
            } else {
                moves.push_back(m);
            }
        }

        // Sort non-TT moves
        if (moves.size() > 1 && moves[0] == tt_move) {
            std::sort(moves.begin() + 1, moves.end(), [&](const Move& move_a, const Move& move_b) {
                return score_move(b, move_a, ply_from_root) > score_move(b, move_b, ply_from_root);
            });
        } else {
            std::sort(moves.begin(), moves.end(), [&](const Move& move_a, const Move& move_b) {
                return score_move(b, move_a, ply_from_root) > score_move(b, move_b, ply_from_root);
            });
        }

        Move best_move = Move::NO_MOVE;
        int best_score = (b.sideToMove() == Color::WHITE) ? -999999 : 999999;

        // Search all moves
        for (const auto& m : moves) {
            // TIME MANAGEMENT: Check if time limit exceeded
            // Check at root and periodically at other levels via nodes_searched counter
            if (check_time()) {
                // Time is up - return best move found so far
                if (best_move == Move::NO_MOVE && moves.size() > 0) {
                    best_move = moves[0];  // Emergency fallback
                }
                break;
            }

            // Check if move is quiet BEFORE making it (for killer/history updates)
            bool is_capture = (b.at(m.to()) != Piece::NONE) || (m.typeOf() == Move::ENPASSANT);
            bool is_quiet = !is_capture && (m.typeOf() != Move::PROMOTION);

            b.makeMove(m);
            int score = minimax(b, depth - 1, alpha, beta, ply_from_root + 1);
            b.unmakeMove(m);

            // TIME MANAGEMENT: Abort if time ran out during recursive call
            if (time_up) {
                if (best_move == Move::NO_MOVE && moves.size() > 0) {
                    best_move = moves[0];  // Emergency fallback
                }
                break;
            }

            if (b.sideToMove() == Color::WHITE) {
                if (score > best_score) {
                    best_score = score;
                    best_move = m;
                }
                alpha = std::max(alpha, score);
                if (beta <= alpha) {
                    alpha_cutoffs++;

                    // Update killers and history for quiet moves
                    if (is_quiet) {
                        int from_idx = m.from().index();
                        int to_idx = m.to().index();
                        history_table[from_idx][to_idx] += depth * depth;

                        if (m != killer_moves[ply_from_root][0]) {
                            killer_moves[ply_from_root][1] = killer_moves[ply_from_root][0];
                            killer_moves[ply_from_root][0] = m;
                        }
                    }
                    break;
                }
            } else {
                if (score < best_score) {
                    best_score = score;
                    best_move = m;
                }
                beta = std::min(beta, score);
                if (beta <= alpha) {
                    alpha_cutoffs++;

                    // Update killers and history for quiet moves
                    if (is_quiet) {
                        int from_idx = m.from().index();
                        int to_idx = m.to().index();
                        history_table[from_idx][to_idx] += depth * depth;

                        if (m != killer_moves[ply_from_root][0]) {
                            killer_moves[ply_from_root][1] = killer_moves[ply_from_root][0];
                            killer_moves[ply_from_root][0] = m;
                        }
                    }
                    break;
                }
            }
        }

        // Store in TT
        int flag;
        if (best_score <= alpha_orig) flag = TT_UPPERBOUND;
        else if (best_score >= beta_orig) flag = TT_LOWERBOUND;
        else flag = TT_EXACT;

        // Normalize mate scores for TT
        int stored_score = best_score;
        if (stored_score > 90000) stored_score += ply_from_root;
        else if (stored_score < -90000) stored_score -= ply_from_root;

        store_tt(hash, stored_score, depth, flag, best_move);

        return best_score;
    }

    Move search(int max_depth, int time_limit_ms = 0) {
        nodes_searched = 0;
        quiescence_nodes = 0;
        tt_hits = tt_misses = tt_cutoffs = alpha_cutoffs = 0;

        // Initialize time management
        search_start_time = std::chrono::steady_clock::now();
        search_time_limit_ms = time_limit_ms;
        time_up = false;

        auto start = search_start_time;  // Reuse the same start time

        Move best_move = Move::NO_MOVE;
        int best_score = 0;
        Move last_completed_move = Move::NO_MOVE;  // Track last fully completed depth

        // Iterative deepening with aspiration windows
        for (int depth = 1; depth <= max_depth; depth++) {
            // Stop if time is already up (previous depth took too long)
            if (time_up) {
                break;
            }
            // ASPIRATION WINDOWS: Use narrow window from depth 2+ (20-40% speedup)
            const int ASPIRATION_WINDOW = 50;
            int alpha, beta;
            bool use_aspiration = false;

            if (depth >= 2 && best_score != 0) {
                alpha = best_score - ASPIRATION_WINDOW;
                beta = best_score + ASPIRATION_WINDOW;
                use_aspiration = true;
            } else {
                alpha = -100000;
                beta = 100000;
            }

            int alpha_original = alpha;
            int beta_original = beta;

            // Search with aspiration window
            int score = minimax(board, depth, alpha, beta, 0);

            // Check for aspiration window failures (only if time didn't run out)
            if (!time_up && use_aspiration && (score <= alpha_original || score >= beta_original)) {
                // Re-search with full window
                score = minimax(board, depth, -100000, 100000, 0);
            }

            // Only use this result if search completed (time didn't run out)
            if (!time_up) {
                TTEntry* entry = probe_tt(board.hash());
                if (entry != nullptr) {
                    last_completed_move = entry->best_move;  // Save completed depth result
                    best_move = last_completed_move;
                    best_score = score;
                }
            } else {
                // Time ran out during this depth - use last completed depth
                // best_move already contains last_completed_move
                break;
            }

            auto now = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start).count();

            // UCI info output with extra stats
            int total_tt = tt_hits + tt_misses;
            float tt_hit_rate = (total_tt > 0) ? (tt_hits * 100.0 / total_tt) : 0.0;
            float qs_pct = (nodes_searched > 0) ? (quiescence_nodes * 100.0 / nodes_searched) : 0.0;

            // Only print info for completed depths
            if (!time_up) {
                std::cout << "info depth " << depth
                          << " score cp " << best_score
                          << " nodes " << nodes_searched
                          << " time " << elapsed
                          << " nps " << (elapsed > 0 ? (nodes_searched * 1000 / elapsed) : 0)
                          << " pv " << uci::moveToUci(best_move)
                          << " tthits " << tt_hits
                          << " ttrate " << (int)tt_hit_rate
                          << " ttcutoffs " << tt_cutoffs
                          << " abcutoffs " << alpha_cutoffs
                          << " qsnodes " << quiescence_nodes
                          << " qspct " << (int)qs_pct
                          << std::endl;
            }
        }

        // Safety: If no move was found (extremely rare), pick first legal move
        if (best_move == Move::NO_MOVE) {
            Movelist moves;
            movegen::legalmoves(moves, board);
            if (moves.size() > 0) {
                best_move = moves[0];
            }
        }

        return best_move;
    }
};

// ============================================================================
// UCI PROTOCOL
// ============================================================================

void uci_loop() {
    Engine engine;
    std::string line, token;

    while (std::getline(std::cin, line)) {
        std::istringstream iss(line);
        iss >> token;

        if (token == "uci") {
            std::cout << "id name PestoPasta C++ v2.0\n";
            std::cout << "id author PestoPasta\n";
            std::cout << "uciok\n";
        }
        else if (token == "isready") {
            std::cout << "readyok\n";
        }
        else if (token == "ucinewgame") {
            engine.clear_tables();
            engine.board.setFen(constants::STARTPOS);
        }
        else if (token == "position") {
            std::string type;
            iss >> type;

            if (type == "startpos") {
                engine.board.setFen(constants::STARTPOS);

                std::string moves_token;
                if (iss >> moves_token && moves_token == "moves") {
                    std::string move_str;
                    while (iss >> move_str) {
                        Move m = uci::uciToMove(engine.board, move_str);
                        engine.board.makeMove(m);
                    }
                }
            }
            else if (type == "fen") {
                std::string fen;
                std::getline(iss, fen);
                // Remove leading space
                if (!fen.empty() && fen[0] == ' ') fen = fen.substr(1);

                // Extract FEN (before "moves" keyword if present)
                size_t moves_pos = fen.find(" moves");
                std::string fen_only = (moves_pos != std::string::npos) ? fen.substr(0, moves_pos) : fen;

                engine.board.setFen(fen_only);

                // Apply moves if present
                if (moves_pos != std::string::npos) {
                    std::istringstream moves_iss(fen.substr(moves_pos + 7));
                    std::string move_str;
                    while (moves_iss >> move_str) {
                        Move m = uci::uciToMove(engine.board, move_str);
                        engine.board.makeMove(m);
                    }
                }
            }
        }
        else if (token == "go") {
            int depth = 100;  // Default to high depth, let time control it
            int wtime = 0, btime = 0, winc = 0, binc = 0, movetime = 0;

            std::string param;
            while (iss >> param) {
                if (param == "depth") {
                    iss >> depth;
                }
                else if (param == "wtime") {
                    iss >> wtime;
                }
                else if (param == "btime") {
                    iss >> btime;
                }
                else if (param == "winc") {
                    iss >> winc;
                }
                else if (param == "binc") {
                    iss >> binc;
                }
                else if (param == "movetime") {
                    iss >> movetime;
                }
            }

            // Calculate time limit (same strategy as Python)
            int time_limit_ms = 0;
            if (movetime > 0) {
                time_limit_ms = movetime;
            } else {
                int our_time = (engine.board.sideToMove() == Color::WHITE) ? wtime : btime;
                int our_inc = (engine.board.sideToMove() == Color::WHITE) ? winc : binc;

                if (our_time > 0) {
                    // Use 1/30th of remaining time + increment
                    // More conservative than Python's 1/25th to avoid timeouts
                    time_limit_ms = (our_time / 30) + our_inc;

                    // Min 100ms, max 10 seconds per move
                    time_limit_ms = std::max(100, std::min(10000, time_limit_ms));
                }
            }

            Move best = engine.search(depth, time_limit_ms);
            std::cout << "bestmove " << uci::moveToUci(best) << std::endl;
        }
        else if (token == "quit") {
            break;
        }
    }
}

int main() {
    uci_loop();
    return 0;
}
