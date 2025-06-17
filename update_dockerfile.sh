#!/bin/bash

# Connect to EC2 and update the Dockerfile
ssh -i "/Users/albertlu/Documents/AWS Instance KeyPair/coco-key.pem" ec2-user@3.15.205.79 << 'EOF'
cd ~/ai-clone
cat > Dockerfile << 'DOCKERFILE'
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm
RUN curl -sL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY utils/ ./utils/
COPY rag/ ./rag/
COPY scripts/ ./scripts/
COPY models/ ./models/
COPY routes/ ./routes/
COPY .env.production ./.env

# Setup data directories
RUN mkdir -p data/rag data/memory

# Build frontend
COPY frontend/ ./frontend/
WORKDIR /app/frontend
RUN npm install
RUN npm run build
WORKDIR /app

# Expose ports
EXPOSE 5002
EXPOSE 3000

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Start the application
CMD ["python", "-m", "backend.app"]
DOCKERFILE

echo "Dockerfile updated successfully!"
EOF
