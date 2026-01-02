# Makefile for PestoPasta Chess Engine
# Compiler and flags
CXX := g++
CXXFLAGS := -std=c++17 -I./chess-library/include
OPTFLAGS := -O3
DEBUGFLAGS := -g -O0 -Wall -Wextra

# Target binary
TARGET := pasta_engine
SOURCE := pasta_engine.cpp

# Default target: build optimized binary
all: $(TARGET)

# Optimized build
$(TARGET): $(SOURCE)
	@echo "Building optimized binary..."
	$(CXX) $(CXXFLAGS) $(OPTFLAGS) -o $(TARGET) $(SOURCE)
	@echo "Build complete: $(TARGET)"

# Debug build
debug: $(SOURCE)
	@echo "Building debug binary..."
	$(CXX) $(CXXFLAGS) $(DEBUGFLAGS) -o $(TARGET) $(SOURCE)
	@echo "Debug build complete: $(TARGET)"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -f $(TARGET)
	@echo "Clean complete"

# Test the engine with UCI commands
test: $(TARGET)
	@echo "Testing UCI protocol..."
	@echo "uci\nisready\nposition startpos\ngo depth 5\nquit" | ./$(TARGET)

# Install dependencies (Python packages)
install-deps:
	pip install -r requirements.txt

# Run local play mode
play: $(TARGET)
	python3 play_vs_cpp.py

# Phony targets
.PHONY: all debug clean test install-deps play
