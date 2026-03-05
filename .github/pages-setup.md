# Quick GitHub Pages Setup

## 🚀 3-Step Setup

### Step 1: Enable GitHub Pages
1. Go to your repo: `ranikrishna-coder/agentwork-simulator`
2. **Settings** → **Pages**
3. Under **Source**, select: **GitHub Actions**
4. Save

### Step 2: Deploy API (Required)
The frontend needs an API backend. Deploy it to Render:

1. Go to [render.com](https://render.com)
2. **New +** → **Web Service**
3. Connect GitHub repo: `ranikrishna-coder/agentwork-simulator`
4. Render auto-detects settings
5. Your API will be at: `https://agentwork-simulator-api.onrender.com`

### Step 3: Configure API URL (Optional)
If your API URL is different:

1. GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Add secret: `API_URL` = `https://your-api-url.com`
3. Or edit workflow default in `.github/workflows/deploy-github-pages.yml`

## ✅ Done!

After pushing to `main`, your app will be at:
- **Frontend**: `https://ranikrishna-coder.github.io/agentwork-simulator/`
- **API**: `https://agentwork-simulator-api.onrender.com` (or your API URL)

The workflow automatically:
- ✅ Builds static files
- ✅ Creates `config.js` with API URL
- ✅ Deploys to GitHub Pages
- ✅ Updates on every push

## 🔧 Troubleshooting

**Can't access?**
- Wait 2-3 minutes for first deployment
- Check **Actions** tab for deployment status
- Verify GitHub Pages is enabled in Settings

**API not connecting?**
- Check API is running: `curl https://agentwork-simulator-api.onrender.com/`
- Verify CORS is configured in API
- Check browser console for errors

