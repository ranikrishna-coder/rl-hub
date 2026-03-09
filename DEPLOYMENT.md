# Deployment Guide

AgentWork Simulator can be deployed using multiple methods. Choose the one that best fits your needs.

## 🔄 Auto-deploy on push to `main`

Every push to the **main** branch can automatically deploy to your Ubuntu/Azure VM.

- **Workflow:** [`.github/workflows/deploy-vm.yml`](.github/workflows/deploy-vm.yml) runs on **push to `main`** and on **manual trigger** (Actions → Deploy to VM → Run workflow).
- **What it does:** SSHs into your VM, pulls latest `main`, installs dependencies, restarts the `agentwork-simulator` systemd service.
- **Setup:** Add GitHub Actions secrets and do a one-time VM setup. Full steps: **[CONFIGURE_AUTO_DEPLOY.md](CONFIGURE_AUTO_DEPLOY.md)**.

**Required GitHub secrets** (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `DEPLOY_HOST` | VM IP or hostname (e.g. `20.51.237.143`) |
| `DEPLOY_USER` | SSH user on the VM (e.g. `azureuser`) |
| `DEPLOY_SSH_KEY` | Full **private** SSH key (for SSH into the VM) |

**Optional:** `DEPLOY_APP_PATH` (default `/var/agentwork/AgentWork-Simulator`), `DEPLOY_SSH_PORT` (default `22`).

After this, **pushing to `main`** will deploy automatically. See [CONFIGURE_AUTO_DEPLOY.md](CONFIGURE_AUTO_DEPLOY.md) for one-time VM setup (clone, venv, systemd, passwordless `systemctl restart`).

---

## ☁️ Deploy to Azure VM

### 1. Create an Azure VM

- In **Azure Portal** → **Virtual machines** → **Create** → **Azure virtual machine**.
- **Image:** Ubuntu Server 22.04 LTS (or 20.04).
- **Size:** e.g. Standard_B2s (2 vCPU, 4 GiB) or larger for training.
- **Authentication:** SSH public key (recommended) or password.
- **Inbound ports:** Allow SSH (22). After setup, open HTTP (80) and/or HTTPS (443) if using a reverse proxy.

### 2. Connect and prepare the server

```bash
ssh azureuser@<VM_PUBLIC_IP>

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python 3.11, pip, git, and curl
sudo apt-get install -y python3.11 python3.11-venv python3-pip git curl
```

### 3. Deploy the application

**Option A: Clone and run with Python (recommended for quick deploy)**

```bash
# Clone (use your repo URL)
git clone https://github.com/ranikrishna-coder/agentwork-simulator.git
cd agentwork-simulator

# Virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Optional: set env (e.g. .env for Jira, SMTP)
# export HOST=0.0.0.0
# export PORT=8000

# Run (for testing)
python -m api.main
```

**Option B: Run with Docker**

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in, then:

git clone https://github.com/ranikrishna-coder/agentwork-simulator.git
cd agentwork-simulator
docker build -t agentwork-simulator .
docker run -d -p 8000:8000 --name agentwork agentwork-simulator
```

### 4. Run as a service (systemd)

Create a systemd unit so the app restarts on reboot. **Use the same path where you cloned the app** (e.g. `/var/agentwork/AgentWork-Simulator` or `/home/azureuser/agentwork-simulator`). Wrong paths cause exit code 203/EXEC.

```bash
sudo nano /etc/systemd/system/agentwork-simulator.service
```

Paste and **replace `APP_ROOT` with your actual app directory** (e.g. `/var/agentwork/AgentWork-Simulator`):

```ini
[Unit]
Description=AgentWork Simulator API
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=APP_ROOT
Environment="PATH=APP_ROOT/venv/bin"
Environment="HOST=0.0.0.0"
Environment="PORT=8000"
ExecStart=APP_ROOT/venv/bin/python -m api.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Example: if the app is at `/var/agentwork/AgentWork-Simulator`, use that for every `APP_ROOT`.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable agentwork-simulator
sudo systemctl start agentwork-simulator
sudo systemctl status agentwork-simulator
```

### 5. Open port 8000 in Azure

- **Azure Portal** → Your VM → **Networking** → **Create port rule**.
- **Inbound port rule:** Port 8000, TCP, Source Any (or your IP for security), Action Allow.
- Access: `http://<VM_PUBLIC_IP>:8000`

### 6. (Optional) Reverse proxy with Nginx + HTTPS

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
sudo nano /etc/nginx/sites-available/agentwork
```

Add:

```nginx
server {
    listen 80;
    server_name your-domain.com;   # or VM public IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/agentwork /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
# If using a domain: sudo certbot --nginx -d your-domain.com
```

### 6b. (Optional) Reverse proxy with Apache + HTTPS

If your VM has Apache instead of Nginx:

```bash
sudo apt-get install -y apache2 libapache2-mod-proxy-uwsgi  # or use proxy_http
sudo a2enmod proxy proxy_http headers
sudo nano /etc/apache2/sites-available/agentwork.conf
```

Add:

```apache
<VirtualHost *:80>
    ServerName your-domain.com
    # Or use your VM IP if no domain

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
    RequestHeader set X-Forwarded-Proto "http"
</VirtualHost>
```

Enable site and reload:

```bash
sudo a2ensite agentwork.conf
sudo apache2ctl configtest && sudo systemctl reload apache2
# For HTTPS with Let's Encrypt: sudo apt-get install certbot python3-certbot-apache
# Then: sudo certbot --apache -d your-domain.com
```

### 7. (Optional) Production: Gunicorn + multiple workers

```bash
source APP_ROOT/venv/bin/activate   # e.g. /var/agentwork/AgentWork-Simulator/venv/bin/activate
pip install gunicorn
gunicorn api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Use this `ExecStart` in the systemd unit instead of `python -m api.main` if you use Gunicorn:
`ExecStart=APP_ROOT/venv/bin/gunicorn api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`

---

## 🚀 Quick Deploy Options

### Option 1: GitHub Actions (Automatic)

The repository includes GitHub Actions workflows that automatically:
- Build and test on every push
- Create deployment packages
- Build Docker images
- **Auto-deploy to your Ubuntu VM** on every push to `main`

**Workflows available:**
- `deploy.yml` - Build and test; create deployment package (artifact)
- `deploy-docker.yml` - Build and push Docker image to GitHub Container Registry
- `deploy-vm.yml` - **SSH deploy to Ubuntu VM**: `git pull`, install deps, restart `agentwork-simulator` service

#### Auto deploy to Ubuntu VM (`deploy-vm.yml`)

On every push to `main`, the workflow can deploy to your VM over SSH. **→ Full configuration steps: [CONFIGURE_AUTO_DEPLOY.md](CONFIGURE_AUTO_DEPLOY.md)**

**One-time setup summary:**

1. **Add repository secrets** (Settings → Secrets and variables → Actions):
   - `DEPLOY_HOST` – VM hostname or IP (e.g. `20.51.237.143`)
   - `DEPLOY_USER` – SSH user (e.g. `azureuser`)
   - `DEPLOY_SSH_KEY` – Full private key content (e.g. from `cat ~/.ssh/id_rsa`). The matching public key must be in the VM’s `~/.ssh/authorized_keys`.
   - Optional: `DEPLOY_APP_PATH` – App directory on the VM (default: `/var/agentwork/AgentWork-Simulator`)
   - Optional: `DEPLOY_SSH_PORT` – SSH port if not 22

2. **On the VM** (one-time): app must already be cloned, venv created, and the `agentwork-simulator` systemd service installed and using the same path. The workflow will `git pull`, install dependencies, and restart the service.

3. **Passwordless sudo for restart** (so the SSH user can restart the service without a password):
   ```bash
   sudo visudo
   # Add line (replace azureuser if different):
   azureuser ALL=(ALL) NOPASSWD: /bin/systemctl restart agentwork-simulator
   ```

After that, every push to `main` triggers a deploy. You can also run it manually: Actions → **Deploy to VM** → **Run workflow**. For deploying without GitHub Actions (SSH + git pull + restart), see **[MANUAL_DEPLOYMENT.md](MANUAL_DEPLOYMENT.md)**.

### Option 2: Docker Deployment

#### Build and Run Locally

```bash
# Build the image
docker build -t agentwork-simulator .

# Run the container
docker run -p 8000:8000 agentwork-simulator

# Or use docker-compose
docker-compose up -d
```

#### Push to Container Registry

```bash
# Tag for GitHub Container Registry
docker tag agentwork-simulator ghcr.io/ranikrishna-coder/agentwork-simulator:latest

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Push
docker push ghcr.io/ranikrishna-coder/agentwork-simulator:latest
```

### Option 3: Traditional VPS/Server

```bash
# On your server
git clone https://github.com/ranikrishna-coder/agentwork-simulator.git
cd agentwork-simulator

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
DATABASE_URL=postgresql://user:password@localhost:5432/agentwork_simulator

# Optional: API settings
API_HOST=0.0.0.0
API_PORT=8000

# Optional: Logging
LOG_LEVEL=INFO
```

## 🔧 Production Considerations

### Using a Process Manager

For production, use a process manager like `systemd`, `supervisor`, or `PM2`:

**systemd service** (`/etc/systemd/system/agentwork-simulator.service`). Replace `APP_ROOT` with your app path (e.g. `/var/agentwork/AgentWork-Simulator`):
```ini
[Unit]
Description=AgentWork Simulator API Server
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=APP_ROOT
Environment="PATH=APP_ROOT/venv/bin"
Environment="HOST=0.0.0.0"
Environment="PORT=8000"
ExecStart=APP_ROOT/venv/bin/python -m api.main
Restart=always
RestartSec=5

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
- Extract: `tar -xzf agentwork-simulator-deployment.tar.gz`
- Install: `pip install -r requirements.txt`
- Run: `python -m api.main`

## 🆘 Troubleshooting

### Service fails with exit code 203/EXEC
The systemd unit is using the wrong path. `WorkingDirectory` and `ExecStart` must point to where the app is actually installed (e.g. `/var/agentwork/AgentWork-Simulator`). Edit the service file, replace every path with your real app root, then run:
```bash
sudo systemctl daemon-reload
sudo systemctl restart agentwork-simulator
```

### Apache "Service Unavailable" (503)
The app behind the reverse proxy is not running. Check: `sudo systemctl status agentwork-simulator` and ensure the app is listening on port 8000: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/`

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

