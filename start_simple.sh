#!/bin/bash
# Simple server start script

echo "RL Hub - Simple Start"
echo "====================================="
echo ""

# Check if we're in the right directory
if [ ! -f "api/main.py" ]; then
    echo "Error: Please run this from the rl-hub directory"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

echo "Step 1: Checking dependencies..."
python3 check_server.py

if [ $? -ne 0 ]; then
    echo ""
    echo "Installing dependencies..."
    pip3 install fastapi uvicorn gymnasium numpy pydantic
fi

echo ""
echo "Step 2: Starting server..."
echo "Server will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start server
python3 -m api.main

