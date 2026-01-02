# PestoPasta Chess Engine

A high-performance chess engine achieving 2000+ ELO on Lichess through optimized C++ implementation with bitboard representation and advanced search algorithms.

## Performance Overview

This project demonstrates a 250x performance improvement through architectural optimization:

| Implementation | Nodes/Second | Speedup |
|----------------|--------------|---------|
| Python Prototype | 10,000 | 1x |
| C++ Bitboards | 2,500,000 | 250x |

**Current Strength:** 2000 ELO on Lichess (Top 10% of players)

## Technical Architecture

### Board Representation
- **Bitboards:** 64-bit integers representing piece positions with bitwise operations for move generation
- **Magic Bitboards:** Efficient sliding piece (rooks, bishops, queens) attack calculation
- **Zobrist Hashing:** Position fingerprinting for transposition table lookups

### Search Algorithm
- **Minimax with Alpha-Beta Pruning:** Exponential reduction in search space
- **Iterative Deepening:** Progressive depth search from 1 to maximum depth
- **Quiescence Search:** Tactical extension to avoid horizon effect
- **Transposition Table:** Caching of previously evaluated positions

### Evaluation Function
- **PeSTO (Piece-Square Tables Only):** Positional evaluation based on piece placement
- **Tapered Evaluation:** Smooth interpolation between middlegame and endgame values
- **Game Phase Calculation:** Dynamic weighting based on remaining material

### Time Management
- **Dynamic Allocation:** Calculates time per move based on remaining clock and increment
- **Emergency Mode:** Reduced search depth when time is critically low
- **Adaptive Depth:** Depth 8 for Blitz, Depth 9 for Rapid, Depth 10 for Classical

## Quick Start

### Local Play

```bash
# Build the engine
make

# Play against the engine in terminal
python3 play_vs_cpp.py
```

### UCI Protocol

The engine implements the Universal Chess Interface (UCI) protocol and can be used with any UCI-compatible GUI:

```bash
./pasta_engine
```

Then send UCI commands:
```
uci
isready
position startpos
go depth 8
quit
```

Compatible GUIs: Arena, CuteChess, Banksia GUI, Lucas Chess

### Live Demo

The engine is deployed as an active bot on Lichess:
- **Profile:** [Your Lichess Bot Username]
- **Challenge the bot:** Visit profile and click "Challenge to a game"
- **Match History:** View all games and opening repertoire

## Project Structure

```
.
├── pasta_engine.cpp          # C++ engine implementation
├── cpp_engine_bridge.py      # Python-C++ bridge for local play
├── lichess_bot.py            # Lichess bot deployment (handles API, time controls)
├── play_vs_cpp.py            # Terminal interface for human vs engine
├── chess-library/            # Chess board library (external)
├── Makefile                  # Build system
└── README.md                 # This file
```

## Dependencies

### C++ Engine
- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- Chess library (included in `chess-library/`)

### Python Components
```bash
pip install -r requirements.txt
```

Required packages:
- `chess` - Python chess library
- `berserk` - Lichess API client
- `requests` - HTTP library

## Build Instructions

### Using Make (Recommended)
```bash
make          # Build optimized binary
make debug    # Build with debug symbols
make clean    # Remove compiled files
```

### Manual Compilation
```bash
g++ -O3 -std=c++17 -I./chess-library/include -o pasta_engine pasta_engine.cpp
```

## Performance Metrics

### Search Speed
- **2.5 million nodes/second** at depth 8 (typical Blitz game)
- **Depth 6:** 0.03 seconds per move (~1500 ELO)
- **Depth 7:** 0.13 seconds per move (~1700 ELO)
- **Depth 8:** 0.74 seconds per move (~1900 ELO)
- **Depth 9:** 3-5 seconds per move (~2100 ELO)
- **Depth 10:** 5-10 seconds per move (~2200+ ELO)

### Memory Efficiency
- Transposition table size: Configurable (default ~256MB)
- Move generation: Zero allocation via bitwise operations

## Deployment

The engine runs as a 24/7 Lichess bot on Koyeb:
- Automatically challenges other bots in Hunter Mode
- Accepts challenges from human players
- Time controls: 3+2 Blitz, 10+5 Rapid, 30+20 Classical
- Adaptive depth based on time control

## License

MIT License - see LICENSE file for details

## Technical Highlights

This project demonstrates:
- **Low-level optimization:** Bitwise operations and cache-efficient data structures
- **Algorithm design:** Alpha-beta pruning reduces search space by orders of magnitude
- **Systems engineering:** Migrating from interpreted Python to compiled C++ for performance
- **API integration:** Lichess Bot API with event streaming and challenge handling
- **Time management:** Dynamic resource allocation under real-time constraints
