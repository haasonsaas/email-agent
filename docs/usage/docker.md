# Docker Deployment Guide

Run the Email Agent in a containerized environment using Docker for consistent, isolated execution across different systems.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/haasonsaas/email-agent.git
cd email-agent

# Build and run with Docker Compose
docker-compose up --build
```

## 🐳 Docker Setup

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- 2GB+ available RAM
- Gmail API credentials

### Build Options

#### Option 1: Docker Compose (Recommended)
```bash
# Build and start services
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

#### Option 2: Manual Docker Build
```bash
# Build the image
docker build -t email-agent .

# Run the container
docker run -it \
  --name email-agent \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/data:/app/data \
  email-agent
```

## 📁 Volume Mounts

The Docker setup uses several volume mounts for persistence:

```yaml
volumes:
  - ./.env:/app/.env                    # Environment configuration
  - ./data:/app/data                    # Database and logs
  - ./credentials:/app/credentials      # OAuth credentials
  - ./Briefs:/app/Briefs               # Generated briefs
```

### Directory Structure
```
email-agent/
├── data/
│   ├── emails.db           # SQLite database
│   └── logs/              # Application logs
├── credentials/
│   ├── client_secret.json # Gmail OAuth client
│   └── token.json         # Access tokens
├── Briefs/                # Generated email briefs
└── .env                   # Environment variables
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file with required configuration:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Gmail Configuration
GMAIL_CLIENT_SECRET_PATH=/app/credentials/client_secret.json
GMAIL_TOKEN_PATH=/app/credentials/token.json

# Database Configuration
DATABASE_PATH=/app/data/emails.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_PATH=/app/data/logs

# TUI Configuration
TUI_REFRESH_INTERVAL=30
TUI_AUTO_SYNC=true
```

### Docker Compose Configuration
```yaml
version: '3.8'

services:
  email-agent:
    build: .
    container_name: email-agent
    restart: unless-stopped
    volumes:
      - ./.env:/app/.env
      - ./data:/app/data
      - ./credentials:/app/credentials
      - ./Briefs:/app/Briefs
    environment:
      - PYTHONUNBUFFERED=1
    ports:
      - "8080:8080"  # Optional: for web interface
    stdin_open: true
    tty: true
```

## 🔧 Container Operations

### Basic Commands

#### Start/Stop Container
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart
```

#### Access Container Shell
```bash
# Interactive shell
docker-compose exec email-agent bash

# Run specific command
docker-compose exec email-agent email-agent --help
```

#### View Logs
```bash
# Follow logs
docker-compose logs -f email-agent

# View last 100 lines
docker-compose logs --tail 100 email-agent
```

### Email Agent Commands in Docker

#### Sync Emails
```bash
# Sync latest emails
docker-compose exec email-agent email-agent sync

# Sync with custom parameters
docker-compose exec email-agent email-agent sync --days 30 --verbose
```

#### Launch TUI Dashboard
```bash
# Interactive dashboard
docker-compose exec email-agent email-agent dashboard
```

#### Generate Brief
```bash
# Generate today's brief
docker-compose exec email-agent email-agent brief

# Generate with date range
docker-compose exec email-agent email-agent brief --start-date 2025-01-01
```

## 📊 Monitoring

### Health Checks
The Dockerfile includes health checks:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"
```

### Container Status
```bash
# Check container status
docker-compose ps

# View resource usage
docker stats email-agent

# Check health status
docker inspect --format='{{.State.Health.Status}}' email-agent
```

### Log Monitoring
```bash
# Monitor application logs
tail -f data/logs/email_agent.log

# Monitor Docker logs
docker-compose logs -f email-agent
```

## 🔒 Security Considerations

### Credential Management
1. **Never commit credentials** to version control
2. **Use Docker secrets** for production deployments
3. **Rotate API keys** regularly
4. **Restrict container permissions**

```bash
# Use Docker secrets (production)
echo "your_api_key" | docker secret create openai_api_key -
```

### Network Security
```yaml
# Production docker-compose.yml
services:
  email-agent:
    networks:
      - email-agent-network
    
networks:
  email-agent-network:
    driver: bridge
    internal: true
```

### File Permissions
```bash
# Set proper permissions for mounted volumes
chmod 600 .env
chmod 700 credentials/
chmod 755 data/
```

## 🚀 Production Deployment

### Multi-stage Build
The Dockerfile uses multi-stage builds for optimization:

```dockerfile
# Build stage
FROM python:3.11-slim as builder
# ... build dependencies and install packages

# Runtime stage  
FROM python:3.11-slim as runtime
# ... copy only necessary files
```

### Resource Limits
```yaml
services:
  email-agent:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Auto-restart Policy
```yaml
services:
  email-agent:
    restart: unless-stopped
    # or
    restart: on-failure:3
```

## 🔧 Troubleshooting

### Common Issues

1. **Permission denied errors**
   ```bash
   # Fix volume permissions
   sudo chown -R 1000:1000 data/ credentials/
   ```

2. **Container won't start**
   ```bash
   # Check logs
   docker-compose logs email-agent
   
   # Verify environment file
   cat .env
   ```

3. **Database locked**
   ```bash
   # Stop all containers
   docker-compose down
   
   # Remove lock files
   rm -f data/*.db-lock
   ```

4. **Memory issues**
   ```bash
   # Increase container memory
   docker-compose up --memory 2g
   ```

### Debug Mode
```bash
# Run with debug logging
docker-compose exec email-agent \
  env EMAIL_AGENT_DEBUG=1 email-agent sync --verbose
```

### Container Inspection
```bash
# Inspect container configuration
docker inspect email-agent

# Check mounted volumes
docker inspect email-agent | jq '.[0].Mounts'

# View environment variables
docker exec email-agent env
```

## 🔄 Backup and Recovery

### Data Backup
```bash
# Backup database and logs
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Backup credentials (secure location)
tar -czf credentials-backup.tar.gz credentials/
```

### Container Backup
```bash
# Export container as image
docker commit email-agent email-agent:backup-$(date +%Y%m%d)

# Save image to file
docker save email-agent:backup-$(date +%Y%m%d) | gzip > email-agent-backup.tar.gz
```

### Recovery
```bash
# Restore from backup
tar -xzf backup-20250131.tar.gz

# Rebuild and restart
docker-compose up --build -d
```

## 📈 Performance Optimization

### Build Optimization
```dockerfile
# Use .dockerignore to exclude unnecessary files
# Multi-stage builds for smaller images
# Cache pip dependencies
```

### Runtime Optimization
```yaml
# Use specific Python image tags
# Optimize memory settings
# Use tmpfs for temporary files
services:
  email-agent:
    tmpfs:
      - /tmp
      - /app/temp
```

### Scaling
```bash
# Run multiple instances (if needed)
docker-compose up --scale email-agent=3
```
