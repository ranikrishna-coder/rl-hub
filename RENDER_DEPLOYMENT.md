# Deploy RL Hub API to Render

Complete step-by-step guide to deploy your FastAPI backend to Render.

## 🚀 Quick Deployment (5 minutes)

### Step 1: Create Render Account

1. Go to [render.com](https://render.com)
2. Click **"Get Started for Free"**
3. Sign up with your **GitHub account** (recommended for easy repo connection)

### Step 2: Create New Web Service

1. In Render dashboard, click **"New +"** button (top right)
2. Select **"Web Service"**

### Step 3: Connect Your GitHub Repository

1. Render will show your GitHub repositories
2. Find and select: **`ranikrishna-coder/rl-hub`**
3. Click **"Connect"**

### Step 4: Configure the Service

Render will auto-detect settings from `render.yaml`, but verify these:

**Basic Settings:**
- **Name**: `rl-hub` (or `rl-hub-api`)
- **Region**: Choose closest to you (e.g., `Oregon (US West)`)
- **Branch**: `main`
- **Root Directory**: Leave empty (or `./` if needed)

**Build & Deploy:**
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python -m api.main`

**Plan:**
- Select **"Free"** (750 hours/month - enough for most use cases)
- Or **"Starter"** ($7/month) for always-on service

### Step 5: Environment Variables (Optional)

Click **"Advanced"** → **"Environment Variables"** to add:

```
PYTHON_VERSION=3.11
PORT=8000
```

(These are usually auto-detected, but you can set them explicitly)

### Step 6: Deploy

1. Click **"Create Web Service"**
2. Render will start building and deploying
3. Wait 5-10 minutes for first deployment

### Step 7: Get Your API URL

After deployment completes:
- Your API will be at: **`https://rl-hub-api.onrender.com`**
- (Or `https://rl-hub-XXXX.onrender.com` if name was taken)

**Save this URL** - you'll need it for GitHub Pages!

## ✅ Verify Deployment

### Test Your API:

```bash
# Test root endpoint
curl https://rl-hub-api.onrender.com/

# Test environments list
curl https://rl-hub-api.onrender.com/environments

# Test API docs
open https://rl-hub-api.onrender.com/docs
```

### Expected Response:

```json
{
  "message": "RL Hub API",
  "version": "1.0.0",
  "endpoints": { ... }
}
```

## 🔄 Auto-Deploy Setup

Render automatically deploys when you push to `main` branch!

**How it works:**
1. You push code: `git push origin main`
2. Render detects the push
3. Render rebuilds and redeploys automatically
4. Your API updates in 5-10 minutes

**No additional setup needed!** It's already configured.

## 🔧 Configuration Details

### render.yaml

Your repo already has `render.yaml` with these settings:

```yaml
services:
  - type: web
    name: rl-hub
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m api.main
    plan: free
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: PORT
        value: 8000
    healthCheckPath: /
    autoDeploy: true
```

Render will use these settings automatically.

## 🌐 Custom Domain (Optional)

### Add Your Own Domain:

1. Go to your service in Render dashboard
2. Click **"Settings"** → **"Custom Domains"**
3. Click **"Add Custom Domain"**
4. Enter your domain (e.g., `api.yourdomain.com`)
5. Follow DNS instructions:
   - Add a CNAME record pointing to Render's provided hostname
6. Render will provision SSL certificate automatically

**Your API will be at:** `https://api.yourdomain.com`

## 📊 Monitoring & Logs

### View Logs:

1. Go to your service in Render dashboard
2. Click **"Logs"** tab
3. See real-time logs and errors

### Health Checks:

Render automatically checks: `GET /`
- If it returns 200, service is healthy
- If it fails, Render will restart the service

## 🐛 Troubleshooting

### Deployment Fails

**Check logs:**
1. Go to Render dashboard → Your service → **"Logs"**
2. Look for error messages
3. Common issues:
   - Missing dependencies in `requirements.txt`
   - Python version mismatch
   - Port binding issues

**Fix common issues:**

```bash
# If dependencies are missing, update requirements.txt
pip freeze > requirements.txt

# If port issue, ensure api/main.py uses:
# port = int(os.getenv("PORT", 8000))
```

### API Not Responding

1. **Check service status** in Render dashboard
2. **Check logs** for errors
3. **Verify health check** endpoint works
4. **Wait 2-3 minutes** - free tier services spin down after inactivity

### Free Tier Limitations

**Free tier:**
- ✅ 750 hours/month
- ✅ Auto-deploys from GitHub
- ✅ HTTPS included
- ⚠️ Spins down after 15 minutes of inactivity
- ⚠️ First request after spin-down takes 30-60 seconds

**To avoid spin-down:**
- Upgrade to **Starter** plan ($7/month) for always-on
- Or use a service like UptimeRobot to ping your API every 5 minutes

### CORS Errors

If your GitHub Pages frontend can't connect:

1. Verify CORS is configured in `api/main.py`
2. Check that your API URL is correct in GitHub Pages `config.js`
3. Test API directly: `curl https://rl-hub-api.onrender.com/`

## 🔐 Environment Variables

### Add Secrets:

1. Render dashboard → Your service → **"Environment"**
2. Click **"Add Environment Variable"**
3. Add variables like:
   - `DATABASE_URL` (if using PostgreSQL)
   - `API_KEY` (if needed)
   - `CORS_ORIGINS` (to restrict CORS)

### Secure Variables:

Render automatically encrypts environment variables. Never commit secrets to git!

## 📈 Scaling

### Free Tier:
- 1 instance
- 512 MB RAM
- Shared CPU

### Starter ($7/month):
- Always-on (no spin-down)
- 512 MB RAM
- Better performance

### Professional ($25/month):
- Multiple instances
- More RAM
- Better for production

## 🔄 Update Your API

### Automatic (Recommended):
Just push to GitHub:
```bash
git add .
git commit -m "Update API"
git push origin main
```
Render auto-deploys in 5-10 minutes.

### Manual:
1. Render dashboard → Your service
2. Click **"Manual Deploy"**
3. Select branch and commit
4. Click **"Deploy"**

## 📝 Next Steps After Deployment

1. **Get your API URL**: `https://rl-hub-api.onrender.com`
2. **Update GitHub Pages**:
   - Go to GitHub repo → Settings → Secrets → Actions
   - Add secret: `API_URL` = `https://rl-hub-api.onrender.com`
3. **Test the connection**:
   - Visit your GitHub Pages site
   - Check browser console for API calls
   - Verify data loads correctly

## 🎯 Quick Checklist

- [ ] Created Render account
- [ ] Created Web Service
- [ ] Connected GitHub repo
- [ ] Configured build/start commands
- [ ] Selected Free plan
- [ ] Deployed successfully
- [ ] Got API URL
- [ ] Tested API endpoints
- [ ] Updated GitHub Pages with API URL
- [ ] Verified frontend connects to API

## 💡 Pro Tips

1. **Use Free tier for testing** - Upgrade when you need always-on
2. **Monitor logs** - Check Render dashboard regularly
3. **Set up alerts** - Render can email you on deployment failures
4. **Use health checks** - Render automatically restarts on failure
5. **Keep dependencies updated** - Update `requirements.txt` regularly

## 🆘 Need Help?

- **Render Docs**: https://render.com/docs
- **Render Status**: https://status.render.com
- **Support**: support@render.com

---

**Your API will be live at:** `https://rl-hub-api.onrender.com` 🚀

