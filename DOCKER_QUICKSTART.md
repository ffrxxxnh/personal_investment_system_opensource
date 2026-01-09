# Docker Quick Start Guide

Get the Personal Investment System running in under 2 minutes with Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+
- 4GB RAM minimum
- 2GB disk space

## Quick Start

```bash
# Clone the repository
git clone https://github.com/ffrxxxnh/personal_investment_system_opensource.git
cd personal_investment_system_opensource

# Start the application
docker-compose up -d

# View logs (optional)
docker-compose logs -f
```

**Access the application at**: http://localhost:5000

## First Run

On first launch, you'll see an onboarding screen with three options:

1. **Demo Mode** - Explore with sample data (recommended for first-time users)
2. **Upload Data** - Import your own CSV/Excel files
3. **Skip** - Go directly to empty dashboard

## Configuration Options

### Change Port

```bash
PIS_PORT=8080 docker-compose up -d
```

### Enable Demo Mode

```bash
DEMO_MODE=true docker-compose up -d
```

### Set Production Secret Key

```bash
# Generate a secure key
SECRET_KEY=$(openssl rand -hex 32)

# Add to docker-compose command
SECRET_KEY=$SECRET_KEY docker-compose up -d
```

### Set Timezone

```bash
TZ=America/New_York docker-compose up -d
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PIS_PORT` | 5000 | Host port mapping |
| `SECRET_KEY` | auto-generated | Flask session key |
| `APP_ENV` | production | Environment mode |
| `DEMO_MODE` | false | Force demo mode |
| `LOG_LEVEL` | INFO | Logging verbosity |
| `TZ` | UTC | Container timezone |
| `FRED_API_KEY` | - | Optional: Federal Reserve API key |

## Data Persistence

Your data is stored in a Docker volume named `pis-investment-data`.

### View Volume

```bash
docker volume inspect pis-investment-data
```

### Backup Data

```bash
# Create backup
docker run --rm -v pis-investment-data:/data -v $(pwd):/backup alpine \
    tar czf /backup/pis-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore Data

```bash
# Restore from backup
docker run --rm -v pis-investment-data:/data -v $(pwd):/backup alpine \
    tar xzf /backup/pis-backup-YYYYMMDD.tar.gz -C /data
```

## Common Commands

```bash
# Start containers
docker-compose up -d

# Stop containers
docker-compose down

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Rebuild after updates
docker-compose build --no-cache
docker-compose up -d

# Shell into container
docker-compose exec pis-web /bin/bash

# Check health
curl http://localhost:5000/health
```

## Troubleshooting

### Port Already in Use

```bash
# Use a different port
PIS_PORT=8080 docker-compose up -d
```

### Permission Denied on Volumes

```bash
# Fix permissions (Linux)
sudo chown -R 1000:1000 ./logs ./output
```

### Container Won't Start

```bash
# Check logs
docker-compose logs pis-web

# Check container status
docker-compose ps
```

### Health Check Failing

The health check has a 60-second startup period. If it keeps failing:

```bash
# Check if app is responding
docker-compose exec pis-web curl http://localhost:5000/health

# Check application logs
docker-compose logs --tail=50 pis-web
```

### Reset Everything

```bash
# Stop and remove containers, networks, and volumes
docker-compose down -v

# Start fresh
docker-compose up -d
```

## Updating

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d
```

## Advanced: Custom Configuration

Mount your own configuration files:

```yaml
# docker-compose.override.yml
services:
  pis-web:
    volumes:
      - ./my-config/settings.yaml:/app/config/settings.yaml:ro
```

## Support

- Report issues: https://github.com/ffrxxxnh/personal_investment_system_opensource/issues
- Documentation: See `docs/` folder
