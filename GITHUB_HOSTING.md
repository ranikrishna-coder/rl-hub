# Hosting RL Hub with GitHub Integration

GitHub itself doesn't host dynamic applications like FastAPI, but we can use **GitHub Actions** to automatically deploy to free hosting platforms. Here are your options:

## 🚀 Option 1: Auto-Deploy to Render (Recommended - Easiest)

Render provides **free hosting** with automatic deployments from GitHub.

### Setup Steps:

1. **Create Render Account:**
   - Go to [render.com](https://render.com)
   - Sign up with your GitHub account

2. **Create New Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository: `ranikrishna-coder/rl-hub`
   - Render will auto-detect the `render.yaml` configuration

3. **Configure Service:**
   - **Name**: `rl-hub`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m api.main`
   - **Plan**: Free (or paid if you need more resources)

4. **Add GitHub Secrets (for auto-deploy):**
   - Go to your GitHub repo → Settings → Secrets and variables → Actions
   - Add these secrets:
     - `RENDER_API_KEY`: Get from Render Dashboard → Account Settings → API Keys
     - `RENDER_SERVICE_ID`: Found in your service URL or API response

5. **Deploy:**
   - Render will automatically deploy on first setup
   - Future pushes to `main` will auto-deploy
   - Your app will be at: **https://rl-hub.onrender.com**

### Access Your App:
- **URL**: `https://rl-hub.onrender.com` (or your custom domain)
- **API Docs**: `https://rl-hub.onrender.com/docs`
- **Catalog**: `https://rl-hub.onrender.com`

---

## 🚂 Option 2: Auto-Deploy to Railway

Railway provides free hosting with GitHub integration.

### Setup Steps:

1. **Create Railway Account:**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

2. **Create New Project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose `ranikrishna-coder/rl-hub`

3. **Configure:**
   - Railway auto-detects Python
   - Uses `railway.json` for configuration
   - Automatically sets up environment

4. **Add GitHub Secret:**
   - Get Railway token: Railway Dashboard → Account → Tokens
   - Add to GitHub: Settings → Secrets → `RAILWAY_TOKEN`

5. **Deploy:**
   - Railway auto-deploys on push
   - Your app will be at: **https://rl-hub-production.railway.app**

### Access Your App:
- **URL**: Check Railway dashboard for your unique URL
- Format: `https://YOUR_APP_NAME.railway.app`

---

## 🐳 Option 3: GitHub Container Registry + Deploy Anywhere

Build Docker image and push to GitHub Container Registry, then deploy anywhere.

### Setup:

1. **The workflow is already set up** (`deploy-docker.yml`)
2. **Push to GitHub** - it will automatically build and push Docker image
3. **Access image**: `ghcr.io/ranikrishna-coder/rl-hub:latest`

### Deploy the Image:

**To any Docker host:**
```bash
docker pull ghcr.io/ranikrishna-coder/rl-hub:latest
docker run -p 8000:8000 ghcr.io/ranikrishna-coder/rl-hub:latest
```

**To Google Cloud Run:**
```bash
gcloud run deploy rl-hub \
  --image ghcr.io/ranikrishna-coder/rl-hub:latest \
  --platform managed \
  --region us-central1
```

---

## 📋 Quick Setup Guide (Render - Recommended)

### Step 1: One-Time Setup on Render

1. Go to [render.com](https://render.com) and sign up
2. Click "New +" → "Web Service"
3. Connect GitHub repo: `ranikrishna-coder/rl-hub`
4. Render will auto-detect settings from `render.yaml`
5. Click "Create Web Service"
6. Wait for first deployment (5-10 minutes)

### Step 2: Get Your Public URL

After deployment, Render shows your URL:
- Example: `https://rl-hub.onrender.com`
- This is your **public URL** - share it with anyone!

### Step 3: Enable Auto-Deploy (Optional)

The workflow `auto-deploy-render.yml` will trigger deployments via GitHub Actions:

1. Get Render API Key:
   - Render Dashboard → Account Settings → API Keys
   - Create new API key

2. Get Service ID:
   - In your service URL: `https://api.render.com/v1/services/SERVICE_ID`
   - Or check Render API response

3. Add GitHub Secrets:
   - GitHub repo → Settings → Secrets and variables → Actions
   - Add `RENDER_API_KEY`
   - Add `RENDER_SERVICE_ID`

Now every push to `main` will trigger a deployment!

---

## 🌐 Custom Domain Setup

### On Render:
1. Go to your service → Settings → Custom Domain
2. Add your domain (e.g., `rl-hub.yourdomain.com`)
3. Follow DNS instructions
4. Access via: `https://rl-hub.yourdomain.com`

### On Railway:
1. Go to your service → Settings → Domains
2. Add custom domain
3. Configure DNS as shown
4. Access via your domain

---

## 🔄 How Auto-Deployment Works

1. **You push code to GitHub** → `git push origin main`
2. **GitHub Actions triggers** → Runs deployment workflow
3. **Workflow deploys to platform** → Render/Railway/etc.
4. **Platform builds and deploys** → Your app goes live
5. **You get a public URL** → Share with the world!

---

## 📊 Comparison of Free Hosting Options

| Platform | Free Tier | Auto-Deploy | Custom Domain | HTTPS |
|----------|-----------|-------------|---------------|-------|
| **Render** | ✅ 750 hrs/month | ✅ Yes | ✅ Yes | ✅ Auto |
| **Railway** | ✅ $5 credit/month | ✅ Yes | ✅ Yes | ✅ Auto |
| **Fly.io** | ✅ 3 VMs free | ✅ Yes | ✅ Yes | ✅ Auto |
| **Heroku** | ❌ No free tier | ✅ Yes | ✅ Yes | ✅ Auto |

**Recommendation**: Start with **Render** - easiest setup and most reliable free tier.

---

## 🎯 Recommended Setup (Render)

```bash
# 1. Push your code (already done)
git push origin main

# 2. Go to render.com and create service
# 3. Connect your GitHub repo
# 4. Render auto-deploys
# 5. Get your URL: https://rl-hub.onrender.com
```

**That's it!** Your app is now live and accessible worldwide.

---

## 🔍 Verify Deployment

After deployment, test your app:

```bash
# Check if it's live
curl https://rl-hub.onrender.com/

# Test API
curl https://rl-hub.onrender.com/environments

# Open in browser
open https://rl-hub.onrender.com
```

---

## 🆘 Troubleshooting

### Deployment Fails:
- Check Render/Railway logs
- Verify `requirements.txt` is correct
- Check Python version compatibility

### Can't Access URL:
- Wait 5-10 minutes for first deployment
- Check service status in dashboard
- Verify DNS if using custom domain

### Auto-Deploy Not Working:
- Check GitHub Actions logs
- Verify secrets are set correctly
- Ensure workflow files are in `.github/workflows/`

---

## 📝 Next Steps

1. **Choose a platform** (Render recommended)
2. **Set up the service** (5 minutes)
3. **Get your public URL**
4. **Share it!** 🎉

Your RL Hub will be accessible at a public URL that anyone can use!

