# Configure Automated Deployment (deploy-vm.yml)

This guide configures the **Deploy to VM** workflow so every push to `main` automatically deploys to your Ubuntu VM.

---

## 1. Add GitHub repository secrets

The workflow needs these secrets to SSH into your VM. **Never commit them to the repo.**

1. Open your repo on GitHub → **Settings** → **Secrets and variables** → **Actions**.
2. Click **New repository secret** and add each of the following.

| Secret name       | Required | Value | Example |
|-------------------|----------|--------|---------|
| `DEPLOY_HOST`     | **Yes**  | VM IP or hostname | `20.51.237.143` |
| `DEPLOY_USER`     | **Yes**  | SSH username on the VM | `azureuser` |
| `DEPLOY_SSH_KEY`  | **Yes**  | Full **private** SSH key (see below) | (multi-line key) |
| `DEPLOY_APP_PATH` | No       | App directory on VM | `/var/agentwork/AgentWork-Simulator` (default) |
| `DEPLOY_SSH_PORT` | No       | SSH port if not 22 | `22` (default) |

### Getting `DEPLOY_SSH_KEY`

**Option A – Use an existing key**

Run this on your **local computer** (your laptop or PC — the same machine where you open a terminal and run `ssh azureuser@<VM_IP>` to connect to the VM). Do **not** run it on the VM itself.

```bash
cat ~/.ssh/id_rsa
```

Copy the **entire** output (including `-----BEGIN ... KEY-----` and `-----END ... KEY-----`) and paste it as the value of `DEPLOY_SSH_KEY`.

**Option B – Create a key only for GitHub Actions**

On your **local computer** (same as above — your laptop/PC, not the VM):

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_vm_key -N ""
```

- Add the **private** key to GitHub:
  ```bash
  cat ~/.ssh/deploy_vm_key
  ```
  Paste that as the secret `DEPLOY_SSH_KEY`.

- Add the **public** key to the VM so GitHub can log in:
  ```bash
  ssh-copy-id -i ~/.ssh/deploy_vm_key.pub azureuser@<VM_IP>
  ```
  Or manually: copy `~/.ssh/deploy_vm_key.pub` and append it to `~/.ssh/authorized_keys` on the VM.

---

## 2. One-time setup on the VM

The app must already be installed and running under systemd. If not, follow [DEPLOYMENT.md](DEPLOYMENT.md) first.

### 2.1 Allow passwordless `systemctl restart`

The SSH user must be able to run **only** the restart command without a password:

```bash
sudo visudo
```

Add this line at the end (replace `azureuser` with `DEPLOY_USER`):

```
azureuser ALL=(ALL) NOPASSWD: /bin/systemctl restart agentwork-simulator
```

Save and exit. Test:

```bash
sudo systemctl restart agentwork-simulator
```

It should not ask for a password.

### 2.2 Ensure git can pull

The app directory must be a git repo and have `origin` pointing to this repository. The user that runs the workflow (`DEPLOY_USER`) must have write access to the directory.

```bash
cd /var/agentwork/AgentWork-Simulator   # or your DEPLOY_APP_PATH
git remote -v
git status
```

If you use HTTPS and the repo is private, you may need a deploy key or token so `git fetch` works without interaction. For a **public** repo, no extra config is needed.

---

## 3. Verify the workflow file

The workflow is in `.github/workflows/deploy-vm.yml`. It:

- **Triggers:** On every push to `main`, or when you run it manually (Actions → Deploy to VM → Run workflow).
- **Does:** Checkout → SSH to VM → `git pull` → `pip install -r requirements.txt` → `sudo systemctl restart agentwork-simulator`.

No changes are needed unless your branch, path, or service name differ. Defaults:

- Branch: `main`
- App path: `/var/agentwork/AgentWork-Simulator` (or `DEPLOY_APP_PATH` secret)
- Service: `agentwork-simulator`

---

## 4. Test automated deployment

1. **Push a small change to `main`:**
   ```bash
   git checkout main
   echo "# deploy test" >> README.md
   git add README.md && git commit -m "chore: test auto deploy" && git push origin main
   ```

2. **Open GitHub** → **Actions** → select the **Deploy to VM** run (triggered by the push).

3. **Check:** The job should complete successfully and the “Deploy via SSH” step should show the script output (git pull, pip install, restart).

4. **On the VM:** Confirm the app is running and serving the latest code:
   ```bash
   sudo systemctl status agentwork-simulator
   curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/
   ```

---

## 5. Run deployment manually

You can deploy without pushing:

1. GitHub → **Actions** → **Deploy to VM**.
2. Click **Run workflow** → choose branch (e.g. `main`) → **Run workflow**.

---

## Troubleshooting

| Problem | What to check |
|--------|----------------|
| **SSH connection failed** | `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` correct; VM allows SSH (port 22 or `DEPLOY_SSH_PORT`); public key in VM `~/.ssh/authorized_keys`. |
| **Permission denied (publickey)** | Private key in `DEPLOY_SSH_KEY` is complete (including BEGIN/END lines); no extra spaces; public key added on VM. |
| **Directory not found** | `DEPLOY_APP_PATH` matches the real path on the VM (e.g. `/var/agentwork/AgentWork-Simulator`). |
| **sudo: no tty present** | Add the NOPASSWD line in `visudo` for `systemctl restart agentwork-simulator` (step 2.1). |
| **Service failed to start** | On VM run `sudo journalctl -u agentwork-simulator -n 50`; fix paths or app errors (see [DEPLOYMENT.md](DEPLOYMENT.md#-troubleshooting)). |
| **git fetch / reset fails** | Repo is git clone; `origin` is correct; if private repo, use deploy key or token so pull works non-interactively. |

---

## Summary checklist

- [ ] Secrets added: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` (and optional `DEPLOY_APP_PATH`, `DEPLOY_SSH_PORT`)
- [ ] VM: Public key for `DEPLOY_SSH_KEY` is in `~/.ssh/authorized_keys`
- [ ] VM: `sudo visudo` has NOPASSWD for `systemctl restart agentwork-simulator`
- [ ] VM: App cloned, venv and systemd service set up; path matches `DEPLOY_APP_PATH` (or default)
- [ ] Pushed to `main` and confirmed a “Deploy to VM” run in Actions

After this, every push to `main` will trigger an automated deployment.
