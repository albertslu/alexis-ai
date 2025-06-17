# AI Clone Deployment Checklist

This checklist will guide you through deploying your AI Clone MVP to production.

## 1. Environment Configuration

- [ ] Create a production `.env` file based on `.env.example`
- [ ] Set secure values for all secrets (JWT_SECRET, API keys, etc.)
- [ ] Configure MongoDB connection string
- [ ] Set FRONTEND_URL to your Vercel domain
- [ ] Configure Google OAuth credentials for production

## 2. Backend Deployment (EC2 with Docker)

### EC2 Instance Setup
- [ ] Launch an EC2 t3.medium instance with Ubuntu 22.04
- [ ] Configure security groups (allow ports 22, 80, 443, 5002)
- [ ] Assign an Elastic IP for a consistent address
- [ ] Set up a domain name pointing to your EC2 instance

### Docker Deployment
- [ ] SSH into your EC2 instance
- [ ] Install Docker and Docker Compose (using `deploy.sh`)
- [ ] Clone your repository: `git clone https://github.com/yourusername/ai-clone.git`
- [ ] Create `.env` file with production values
- [ ] Start the application: `docker-compose up -d`
- [ ] Set up Nginx as a reverse proxy (optional but recommended)
- [ ] Configure SSL with Let's Encrypt

## 3. Frontend Deployment (Vercel)

- [ ] Create `.env.production` in the frontend directory with:
  ```
  REACT_APP_API_URL=https://api.your-domain.com
  ```
- [ ] Install Vercel CLI: `npm install -g vercel`
- [ ] Deploy to Vercel:
  ```
  cd frontend
  vercel
  ```
- [ ] For production deployment: `vercel --prod`
- [ ] Configure environment variables in Vercel dashboard

## 4. MongoDB Configuration

- [ ] Ensure your MongoDB instance is accessible from your EC2 instance
- [ ] Set up proper authentication for MongoDB
- [ ] Create necessary indexes for performance
- [ ] Set up regular backups

## 5. Testing the Deployment

- [ ] Test user registration and login
- [ ] Test data integration (iMessage, Gmail, LinkedIn)
- [ ] Test chat functionality
- [ ] Test feedback system
- [ ] Test auto-response functionality
- [ ] Verify proper data isolation between users

## 6. Post-Deployment Tasks

- [ ] Set up monitoring (CloudWatch, Sentry, etc.)
- [ ] Configure logging
- [ ] Set up CI/CD for automated deployments
- [ ] Create a rollback plan in case of issues
