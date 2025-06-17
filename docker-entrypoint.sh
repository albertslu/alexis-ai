#!/bin/bash
set -e

# Create necessary directories
mkdir -p /app/data/rag
mkdir -p /app/data/memory
mkdir -p /app/data/chat_histories
mkdir -p /app/data/user_configs
mkdir -p /app/models
mkdir -p /app/logs

# Set proper permissions
chmod -R 755 /app/data
chmod -R 755 /app/models
chmod -R 755 /app/logs

# Print environment info (redacted)
echo "Starting AI Clone with:"
echo "- MongoDB: $(echo $MONGO_URI | sed 's/\/\/.*@/\/\/***:***@/')"
echo "- Frontend URL: $FRONTEND_URL"
echo "- AI Model: $AI_MODEL"

# Start the application
exec "$@"
