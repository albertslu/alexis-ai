# AI Clone Deployment Guide

This guide will help you deploy the AI Clone system for a limited release (10-15 users).

## Deployment Architecture

For a small user base, we'll use a simplified architecture:
- Single EC2 instance running Docker
- Local file storage for RAG, memories, and SQLite database
- OpenAI API for the fine-tuned model

## Prerequisites

1. AWS account
2. Domain name (optional but recommended)
3. OpenAI API key
4. Google Cloud Console project with OAuth credentials

## Step 1: Set Up EC2 Instance

1. Launch an EC2 instance:
   - Amazon Linux 2 or Ubuntu 20.04+
   - t3.large instance type (4 vCPU, 8GB RAM)
   - At least 30GB EBS storage
   - Security group allowing ports 22 (SSH), 80 (HTTP), 443 (HTTPS), and 5002 (API)

2. SSH into your instance:
   ```bash
   ssh -i your-key.pem ec2-user@your-instance-ip
   ```

## Step 2: Install Dependencies

Run the included deployment script:
```bash
chmod +x deploy.sh
./deploy.sh
```

## Step 3: Configure Environment Variables

Create a `.env` file in your project root:
```
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
AI_MODEL=ft:gpt-4o-mini-2024-07-18:al43595::BCX8dk0Q

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
FRONTEND_URL=https://your-domain.com

# Server Configuration
FLASK_ENV=production
```

## Step 4: Data Migration

### Option 1: Start Fresh
Let users connect their data sources through the UI.

### Option 2: Migrate Existing Data
1. Create a `data` directory on your EC2 instance
2. Copy your local data to the server:
   ```bash
   scp -r -i your-key.pem ./data/* ec2-user@your-instance-ip:~/ai-clone/data/
   ```

## Step 5: Deploy with Docker Compose

```bash
docker-compose up -d
```

## Step 6: Set Up Domain and SSL (Optional)

1. Register a domain and point it to your EC2 instance IP
2. Install Nginx as a reverse proxy:
   ```bash
   sudo apt-get install nginx
   ```

3. Configure Nginx:
   ```
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:5002;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

4. Set up SSL with Let's Encrypt:
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

## Storage Considerations

### RAG Database
- Stored in `/app/data/rag/` inside the container
- Mounted to `./data/rag/` on the host for persistence
- No need for MongoDB for a limited release

### Letta Memories
- Stored in `/app/data/memory/` inside the container
- Mounted to `./data/memory/` on the host for persistence

### SQLite Database
- Stored in the container and persisted through the volume mount
- Sufficient for 10-15 users

## Scaling Considerations (Future)

If you need to scale beyond 15 users:
1. Migrate SQLite to PostgreSQL
2. Move file storage to S3
3. Consider a multi-container architecture with separate services

## Monitoring and Maintenance

1. Check logs:
   ```bash
   docker-compose logs -f
   ```

2. Update the application:
   ```bash
   git pull
   docker-compose down
   docker-compose up -d --build
   ```

3. Backup data:
   ```bash
   tar -czvf ai-clone-backup.tar.gz ./data
   ```
