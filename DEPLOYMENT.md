# Deployment Guide

RL Hub can be deployed using multiple methods. Choose the one that best fits your needs.

## 🚀 Quick Deploy Options

### Option 1: GitHub Actions (Automatic)

The repository includes GitHub Actions workflows that automatically:
- Build and test on every push
- Create deployment packages
- Build Docker images
- Deploy to various platforms

**Workflows available:**
- `deploy.yml` - General deployment package
- `deploy-docker.yml` - Build and push Docker image to GitHub Container Registry
- `deploy-railway.yml` - Deploy to Railway
- `deploy-render.yml` - Deploy to Render
- `deploy-flyio.yml` - Deploy to Fly.io

### Option 2: Docker Deployment

#### Build and Run Locally

```bash
# Build the image
docker build -t rl-hub .

# Run the container
docker run -p 8000:8000 rl-hub

# Or use docker-compose
docker-compose up -d
```

#### Push to Container Registry

```bash
# Tag for GitHub Container Registry
docker tag rl-hub ghcr.io/ranikrishna-coder/rl-hub:latest

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Push
docker push ghcr.io/ranikrishna-coder/rl-hub:latest
```

### Option 3: Railway

1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Initialize: `railway init`
4. Deploy: `railway up`

Or use the GitHub Action with `RAILWAY_TOKEN` secret.

### Option 4: Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python -m api.main`
5. Add environment variables if needed

Or use the GitHub Action with `RENDER_API_KEY` and `RENDER_SERVICE_ID` secrets.

### Option 5: Fly.io

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Launch: `fly launch`
4. Deploy: `fly deploy`

Or use the GitHub Action with `FLY_API_TOKEN` secret.

### Option 6: Traditional VPS/Server

```bash
# On your server
git clone https://github.com/ranikrishna-coder/rl-hub.git
cd rl-hub

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run with systemd or supervisor
python -m api.main
```

## 📋 Environment Variables

Create a `.env` file or set environment variables:

```bash
# Optional: Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/rl_hub

# Optional: API settings
API_HOST=0.0.0.0
API_PORT=8000

# Optional: Logging
LOG_LEVEL=INFO
```

## 🔧 Production Considerations

### Using a Process Manager

For production, use a process manager like `systemd`, `supervisor`, or `PM2`:

**systemd service** (`/etc/systemd/system/rl-hub.service`):
```ini
[Unit]
Description=RL Hub API Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/rl-hub
Environment="PATH=/opt/rl-hub/venv/bin"
ExecStart=/opt/rl-hub/venv/bin/python -m api.main
Restart=always

[Install]
WantedBy=multi-user.target
```

### Using Gunicorn (Recommended for Production)

```bash
pip install gunicorn
gunicorn api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🐳 Docker Compose with Database

Uncomment the PostgreSQL service in `docker-compose.yml` and set `DB_PASSWORD`:

```bash
DB_PASSWORD=your_secure_password docker-compose up -d
```

## 📊 Monitoring

The application includes health check endpoints:
- `GET /` - API status
- `GET /environments` - List all environments
- `GET /validate-all` - Validate all environments

## 🔐 Security

1. **Use HTTPS**: Always use HTTPS in production (Let's Encrypt, Cloudflare, etc.)
2. **Environment Variables**: Never commit secrets to git
3. **Firewall**: Restrict access to necessary ports only
4. **Updates**: Keep dependencies updated regularly

## 📦 Deployment Artifacts

GitHub Actions automatically creates deployment packages:
- Download from Actions → Artifacts
- Extract: `tar -xzf rl-hub-deployment.tar.gz`
- Install: `pip install -r requirements.txt`
- Run: `python -m api.main`

## 🆘 Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>
```

### Dependencies Missing
```bash
pip install -r requirements.txt
```

### Import Errors
Make sure you're in the project root and Python path is correct:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## 📚 Additional Resources

- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Docker Documentation](https://docs.docker.com/)
- [GitHub Actions](https://docs.github.com/en/actions)

