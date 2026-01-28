#!/bin/bash

# TPO Analysis Web Application Startup Script

echo "=========================================="
echo "TPO Analysis Web Platform"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Start the application
echo ""
echo "=========================================="
echo "🚀 Starting web server..."
echo "=========================================="
echo ""
echo "📊 Access the application at:"
echo "   http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python web_app.py
