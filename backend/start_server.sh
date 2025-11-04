#!/bin/bash

# KIME Chat Backend Server Start Script
# Ensures only one instance runs at a time

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="/Users/jtm427/miniconda3/envs/openai/bin/python"
SERVER_SCRIPT="$SCRIPT_DIR/api_server.py"
PORT=8000

echo "🚀 KIME Chat Backend Server Starter"
echo "====================================="

# Check if port is already in use
if lsof -ti:$PORT > /dev/null 2>&1; then
    echo "⚠️  Port $PORT is already in use"
    echo "📋 Current processes on port $PORT:"
    lsof -ti:$PORT | while read pid; do
        ps -p $pid -o pid,comm,args | tail -n +2
    done

    read -p "❓ Kill existing processes and restart? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔪 Killing existing processes..."
        lsof -ti:$PORT | xargs kill -9 2>/dev/null
        sleep 2
        echo "✅ Processes killed"
    else
        echo "❌ Aborting. Please manually stop the server first."
        exit 1
    fi
fi

# Check if Python environment exists
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Error: Python not found at $PYTHON_PATH"
    echo "Please update PYTHON_PATH in this script"
    exit 1
fi

# Check if server script exists
if [ ! -f "$SERVER_SCRIPT" ]; then
    echo "❌ Error: Server script not found at $SERVER_SCRIPT"
    exit 1
fi

# Start the server
echo "🎬 Starting server..."
echo "   Python: $PYTHON_PATH"
echo "   Script: $SERVER_SCRIPT"
echo "   Port: $PORT"
echo ""

cd "$SCRIPT_DIR"
$PYTHON_PATH $SERVER_SCRIPT

# If server exits, show message
echo ""
echo "🛑 Server stopped"
