# How to Access AgentWork Simulator

The AgentWork Simulator application runs on **port 8000** and is accessible through different URLs depending on your deployment method.

## 🌐 Access URLs by Deployment Method

### 1. **Local Development**

When running locally on your machine:

```bash
python -m api.main
```

**Access URLs:**
- Main Catalog: **http://localhost:8000**
- API Documentation: **http://localhost:8000/docs**
- Alternative Docs: **http://localhost:8000/redoc**
- API Endpoints: **http://localhost:8000/environments**

**Note:** Only accessible from your local machine.

---

### 2. **Docker Deployment**

#### Local Docker:
```bash
docker run -p 8000:8000 agentwork-simulator
# or
docker-compose up
```

**Access URLs:**
- **http://localhost:8000** (same as local development)

#### Docker on Server/VPS:
If deployed on a server with public IP:

```bash
docker run -p 8000:8000 agentwork-simulator
```

**Access URLs:**
- **http://YOUR_SERVER_IP:8000**
- Example: `http://192.168.1.100:8000`

**To make it accessible from anywhere:**
1. Ensure firewall allows port 8000
2. Use your server's public IP address
3. Or set up a domain name pointing to your IP

---

### 3. **GitHub Container Registry (Docker)**

If you deploy the Docker image to a cloud provider:

**Access depends on where you deploy:**
- **AWS ECS/Fargate**: Use load balancer URL
- **Google Cloud Run**: `https://YOUR_SERVICE.run.app`
- **Azure Container Instances**: Use public IP or domain
- **DigitalOcean App Platform**: Auto-generated URL

---

### 4. **Traditional VPS/Server**

If deployed on a VPS (AWS EC2, DigitalOcean, Linode, etc.):

**Access URLs:**
- **http://YOUR_SERVER_IP:8000** (if port 8000 is open)
- **https://yourdomain.com** (if using reverse proxy)

**Setup Steps:**

1. **Open Firewall Port:**
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 8000/tcp
   
   # CentOS/RHEL
   sudo firewall-cmd --add-port=8000/tcp --permanent
   sudo firewall-cmd --reload
   ```

2. **Run the Application:**
   ```bash
   python -m api.main
   # or use systemd/supervisor for production
   ```

3. **Access via IP:**
   - Find your server's public IP
   - Access: `http://YOUR_PUBLIC_IP:8000`

4. **Setup Domain (Optional):**
   - Point your domain's A record to your server IP
   - Use Nginx/Caddy as reverse proxy
   - Access via: `https://yourdomain.com`

---

## 🔒 HTTPS Setup (Production)

For production, always use HTTPS:

### Option 1: Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then use Let's Encrypt:
```bash
sudo certbot --nginx -d yourdomain.com
```

### Option 2: Cloudflare
- Add your domain to Cloudflare
- Enable "Proxy" (orange cloud)
- SSL/TLS mode: Full or Full (strict)

---

## 📱 Accessing from Different Devices

### Same Network (Local):
- **Desktop/Laptop**: `http://localhost:8000`
- **Mobile (same WiFi)**: `http://YOUR_COMPUTER_IP:8000`
  - Find IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)

### Internet (Public):
- Use the public URL provided by your deployment platform
- Or your domain name if configured

---

## 🔍 Testing Access

### Check if App is Running:
```bash
# Local
curl http://localhost:8000/

# Remote
curl http://YOUR_URL/
```

### Expected Response:
```json
{
  "message": "AgentWork Simulator API",
  "version": "1.0.0",
  "endpoints": { ... }
}
```

### Test API Endpoints:
```bash
# List environments
curl http://YOUR_URL/environments

# Get environment metadata
curl http://YOUR_URL/environment/TreatmentPathwayOptimization/metadata

# Validate environment
curl http://YOUR_URL/validate/TreatmentPathwayOptimization
```

---

## 🌍 Public vs Private Access

### Public Access (Internet):
- ✅ Cloud platforms (Azure, Docker on cloud)
- ✅ VPS with public IP and open firewall
- ✅ Domain name pointing to your server

### Private Access (Local Network):
- ✅ Local development (`localhost`)
- ✅ Docker on local machine
- ✅ Server on local network (LAN IP)

### Restricted Access:
- 🔒 Behind VPN
- 🔒 Firewall blocking port 8000
- 🔒 Private network only

---

## 🚀 Quick Access Summary

| Deployment | Default URL | HTTPS | Custom Domain |
|------------|------------|-------|---------------|
| **Local** | `http://localhost:8000` | ❌ | ❌ |
| **Docker** | `http://localhost:8000` | ❌ | ✅ (if configured) |
| **Azure** | `https://your-app.azurewebsites.net` | ✅ | ✅ |
| **VPS** | `http://IP:8000` | ✅ (with setup) | ✅ |

---

## 📝 Environment Variables for Port Configuration

You can customize the port using environment variables:

```bash
# Set custom port
export PORT=8080
python -m api.main
```

Or modify `api/main.py`:
```python
import os
port = int(os.getenv("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
```

---

## 🆘 Troubleshooting Access Issues

### Can't Access Locally:
- ✅ Check if app is running: `ps aux | grep api.main`
- ✅ Check port: `lsof -i :8000`
- ✅ Try `127.0.0.1:8000` instead of `localhost:8000`

### Can't Access Remotely:
- ✅ Check firewall rules
- ✅ Verify port is open: `telnet YOUR_IP 8000`
- ✅ Check if app binds to `0.0.0.0` (not `127.0.0.1`)
- ✅ Verify DNS records (if using domain)

### HTTPS Issues:
- ✅ Check SSL certificate validity
- ✅ Verify reverse proxy configuration
- ✅ Check Cloudflare SSL mode

---

## 📞 Need Help?

- Check deployment logs in your platform's dashboard
- Review `DEPLOYMENT.md` for deployment-specific issues
- Check GitHub Actions logs for build/deploy errors

