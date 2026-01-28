# Deploying to Render

## Prerequisites

1. A [Render account](https://render.com) (free tier available)
2. Your code pushed to a Git repository (GitHub, GitLab, or Bitbucket)
3. Supabase credentials ready

## Step-by-Step Deployment

### Method 1: Using Render Dashboard (Recommended for first-time)

#### 1. Push Your Code to GitHub

```bash
# If not already initialized
git init
git add .
git commit -m "Prepare for Render deployment"

# Push to GitHub
git remote add origin https://github.com/yourusername/your-repo.git
git branch -M main
git push -u origin main
```

#### 2. Create New Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub/GitLab account if not already connected
4. Select your repository from the list

#### 3. Configure Your Service

Fill in the following settings:

| Setting | Value |
|---------|-------|
| **Name** | `tpo-analysis-app` (or your preferred name) |
| **Region** | Choose closest to your users |
| **Branch** | `main` |
| **Root Directory** | Leave blank |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn --bind 0.0.0.0:$PORT web_app:app` |

#### 4. Add Environment Variables

In the "Environment Variables" section, add:

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | `https://yjocerexovxaaizuuzji.supabase.co` |
| `SUPABASE_KEY` | `eyJhbGciOi...` (your full key) |
| `PYTHON_VERSION` | `3.12.0` |

**Important:** Click the 🔒 icon next to `SUPABASE_KEY` to mark it as secret.

#### 5. Choose Instance Type

- **Free Tier**: Free but spins down after inactivity (takes ~30s to wake up)
- **Starter ($7/mo)**: Always on, better performance

#### 6. Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Start your application
3. Monitor deployment logs in real-time
4. Once deployed, you'll get a URL like: `https://tpo-analysis-app.onrender.com`

### Method 2: Using render.yaml (Infrastructure as Code)

The `render.yaml` file is already created in your project.

1. Push your code including `render.yaml` to GitHub
2. Go to Render Dashboard → **"New +"** → **"Blueprint"**
3. Connect your repository
4. Render will detect `render.yaml` and configure everything automatically
5. Still need to add environment variables manually (security best practice)

## Post-Deployment Configuration

### 1. Set Custom Domain (Optional)

1. Go to your service → **"Settings"** → **"Custom Domain"**
2. Add your domain and configure DNS records as shown

### 2. Enable Auto-Deploy

1. Go to **"Settings"** → **"Build & Deploy"**
2. Enable **"Auto-Deploy"** to deploy on every git push

### 3. Configure Health Checks

Render automatically monitors your app. For custom health checks:

1. Go to **"Settings"** → **"Health & Alerts"**
2. Set health check path to `/` (your main page)

## Monitoring Your App

### View Logs
- Dashboard → Your Service → **"Logs"** tab
- Real-time logs show all application output

### Metrics
- Dashboard → Your Service → **"Metrics"** tab
- Monitor CPU, memory, and response times

### Shell Access
- Click **"Shell"** tab to access your app's container
- Useful for debugging

## Updating Your App

### Automatic Updates (if Auto-Deploy enabled)
```bash
git add .
git commit -m "Update feature"
git push origin main
# Render automatically redeploys
```

### Manual Deploy
- Dashboard → Your Service → **"Manual Deploy"** → **"Deploy latest commit"**

## Troubleshooting

### App Not Starting

**Check Build Logs:**
1. Go to your service → **"Events"** tab
2. Look for errors in build/deploy process

**Common Issues:**

1. **Missing dependencies**
   - Ensure all packages are in `requirements.txt`
   - Run locally: `pip freeze > requirements.txt`

2. **Port binding error**
   - Render provides `$PORT` environment variable
   - Our start command handles this: `gunicorn --bind 0.0.0.0:$PORT`

3. **Import errors**
   - Check that all file paths are relative
   - Verify all Python files are committed

### Environment Variables Not Working

1. Check spelling (case-sensitive)
2. Verify values are correct (no extra spaces)
3. Restart service after adding/changing variables:
   - **"Settings"** → **"Manual Deploy"** → **"Clear build cache & deploy"**

### Database Connection Issues

1. Verify `SUPABASE_URL` and `SUPABASE_KEY` are set correctly
2. Check Supabase dashboard for any IP restrictions
3. Test connection in Render Shell:
   ```bash
   python -c "from supabase_client import get_supabase_client; print('Connected!')"
   ```

### Slow Performance

**Free Tier Limitations:**
- Spins down after 15 minutes of inactivity
- Takes ~30 seconds to wake up on first request

**Solutions:**
1. Upgrade to Starter plan ($7/mo) for always-on service
2. Use a ping service (UptimeRobot) to keep it alive
3. Add a loading message for users

## Cost Estimates

| Plan | Price | Best For |
|------|-------|----------|
| **Free** | $0/mo | Testing, personal projects |
| **Starter** | $7/mo | Production apps, always-on |
| **Standard** | $25/mo | Higher traffic, better resources |

## Security Best Practices

1. ✅ Environment variables (not hardcoded) - **Already done!**
2. ✅ `.env` in `.gitignore` - **Already done!**
3. 🔒 Enable HTTPS (automatic on Render)
4. 🔒 Rotate Supabase keys regularly
5. 🔒 Set up RLS policies in Supabase for production

## Useful Render CLI Commands

Install Render CLI:
```bash
brew install render  # macOS
# or
npm install -g @render/cli
```

Deploy from terminal:
```bash
render login
render services list
render deploy <service-id>
```

## Support

- [Render Documentation](https://render.com/docs)
- [Render Community](https://community.render.com/)
- [Status Page](https://status.render.com/)

## Your App URLs

After deployment:
- **Production**: `https://tpo-analysis-app.onrender.com`
- **Dashboard**: `https://dashboard.render.com/`
- **Logs**: Dashboard → Your Service → Logs tab

---

**Ready to deploy?** Follow Method 1 above step-by-step! 🚀
