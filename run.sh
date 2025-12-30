#!/bin/bash

# Ensure .env exists or warn user
if [ ! -f .env ] && [ -z "$OPENROUTER_API_KEY" ]; then
    echo "Error: OPENROUTER_API_KEY is not set and no .env file found."
    echo "Please create a .env file with OPENROUTER_API_KEY=... or export it directly."
    exit 1
fi

echo "Starting Email Agent..."
python3 email_agent.py
