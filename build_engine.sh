#!/bin/bash
# Build script for PestoPasta C++ Engine

echo "🔨 Building PestoPasta C++ Engine..."

# Check if g++ is available
if ! command -v g++ &> /dev/null; then
    echo "❌ g++ not found! Install with: brew install gcc"
    exit 1
fi

# Compile with optimizations
g++ -O3 -std=c++17 -I./chess-library/include -o pasta_engine pasta_engine.cpp

if [ $? -eq 0 ]; then
    echo "✓ Build successful: pasta_engine"
    echo ""
    echo "Test it manually:"
    echo "  ./pasta_engine"
    echo "  (then type: uci, isready, position startpos, go depth 5, quit)"
    echo ""
    echo "Or run the Python bridge test:"
    echo "  python3 cpp_engine_bridge.py"
else
    echo "❌ Build failed!"
    exit 1
fi
