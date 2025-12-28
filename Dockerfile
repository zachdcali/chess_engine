# Use Python 3.11 slim image (includes C++ compiler)
FROM python:3.11-slim

# Install C++ compiler and build tools
RUN apt-get update && apt-get install -y \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all files to the container
COPY . .

# Compile the C++ engine with optimizations
RUN g++ -O3 -std=c++17 -I./chess-library/include -o pasta_engine pasta_engine.cpp

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot (Python wrapper uses compiled C++ engine)
CMD ["python", "lichess_bot.py"]
