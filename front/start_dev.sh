#!/bin/bash

# KIME Chat Frontend Dev Server Start Script
# Ensures only one instance runs at a time

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=3000

echo "🚀 KIME Chat Frontend Dev Server Starter"
echo "=========================================="

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

# Check if node_modules exists
if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
    echo "⚠️  node_modules not found. Running npm install..."
    cd "$SCRIPT_DIR"
    npm install
fi

# Start the dev server
echo "🎬 Starting frontend dev server..."
echo "   Directory: $SCRIPT_DIR"
echo "   Port: $PORT"
echo ""

cd "$SCRIPT_DIR"
npm run dev

# If server exits, show message
echo ""
echo "🛑 Dev server stopped"
