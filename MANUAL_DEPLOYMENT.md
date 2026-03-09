# Manual Deployment Guide

Use this guide to deploy the latest code to your Ubuntu VM after a new commit, without using GitHub Actions auto-deploy.

**Prerequisites:** The app is already set up on the VM (clone, venv, systemd service, and Apache reverse proxy). See [DEPLOYMENT.md](DEPLOYMENT.md) for initial setup.

---

## Steps

### 1. SSH into the VM

```bash
ssh azureuser@<VM_IP>
```

Replace `<VM_IP>` with your VM’s IP or hostname (e.g. `20.51.237.143`).

---

### 2. Go to the app directory

```bash
cd /var/agentwork/AgentWork-Simulator
```

If your app is installed elsewhere, use that path instead (same as `APP_ROOT` in your systemd service).

---

### 3. Pull latest code

```bash
git fetch origin main
git reset --hard origin/main
```

- Use `git pull origin main` if you prefer merge over hard reset.
- For a different branch, replace `main` with your branch name.

---

### 4. Install or update dependencies

Using the project venv directly:

```bash
/var/agentwork/AgentWork-Simulator/venv/bin/pip install -q --upgrade pip
/var/agentwork/AgentWork-Simulator/venv/bin/pip install -q -r requirements.txt
```

Or with venv activated:

```bash
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
deactivate
```

---

### 5. Restart the app service

```bash
sudo systemctl restart agentwork-simulator
```

---

### 6. Verify deployment

```bash
sudo systemctl status agentwork-simulator
```

Then check the API responds:

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/
```

You should see `200`. If using Apache, also test via the public URL (e.g. `http://<VM_IP>/`).

---

## One-liner (after SSH)

From the app directory:

```bash
cd /var/agentwork/AgentWork-Simulator && git fetch origin main && git reset --hard origin/main && venv/bin/pip install -q -r requirements.txt && sudo systemctl restart agentwork-simulator && sudo systemctl status agentwork-simulator
```

Adjust the path if your app is not in `/var/agentwork/AgentWork-Simulator`.

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| `git reset` fails or conflicts | Run `git status` and resolve conflicts, or use `git pull origin main` instead of `git reset --hard`. |
| Service won’t start (e.g. 203/EXEC) | Check paths in `/etc/systemd/system/agentwork-simulator.service` match your app directory. See [DEPLOYMENT.md](DEPLOYMENT.md#service-fails-with-exit-code-203exec). |
| Apache “Service Unavailable” (503) | Ensure the app is running: `sudo systemctl status agentwork-simulator` and that port 8000 responds locally. |
| Permission denied on `git pull` | Ensure the SSH user owns the repo directory or has write access; use `sudo` only if the repo is under a system path and owned by root. |

---

## See also

- [DEPLOYMENT.md](DEPLOYMENT.md) – Full deployment and initial VM setup
- **Auto deploy** – GitHub Actions “Deploy to VM” workflow (see DEPLOYMENT.md → Auto deploy to Ubuntu VM)
