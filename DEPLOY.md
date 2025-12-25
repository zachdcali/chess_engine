# PestoPasta-Bot Deployment Guide

## Quick Deployment to Koyeb (Free, Always-On)

### Prerequisites
- GitHub account
- Lichess Bot account with API token

### Step 1: Push to GitHub

1. Create a new **private** repository on GitHub (e.g., `pestopasta-bot`)
2. In your terminal:

```bash
cd /Users/zachdodson/Documents/chess_engine
git init
git add agent_minimax.py lichess_bot.py requirements.txt Dockerfile .gitignore
git commit -m "Initial commit: PestoPasta-Bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/pestopasta-bot.git
git push -u origin main
```

### Step 2: Deploy to Koyeb

1. Go to [koyeb.com](https://www.koyeb.com) and sign up (free)
2. Click **"Create App"**
3. Choose **"GitHub"** as the source
4. Connect your GitHub account and select your `pestopasta-bot` repository
5. Choose **"Dockerfile"** as the build method
6. Under **"Environment Variables"**, add:
   - Key: `LICHESS_TOKEN`
   - Value: `your_lichess_token_here`
7. Click **"Deploy"**

### Step 3: Verify

- Your bot should come online within 2-3 minutes
- Check the logs in Koyeb to see "🤖 PestoPasta-Bot is now online!"
- Visit `https://lichess.org/@/PestoPasta-Bot` to see the green dot

---

## Local Testing (Before Deployment)

To test locally with the environment variable:

```bash
export LICHESS_TOKEN="your_lichess_token_here"
source .venv/bin/activate
python lichess_bot.py
```

---

## Alternative Platforms

### Render.com
- Free tier available but sleeps after 15 minutes of inactivity
- Good for testing, not ideal for 24/7 bot

### Railway.app
- Used to have free tier, now requires payment

### Fly.io
- Has free tier with limitations
- More complex setup than Koyeb
