# 🚂 Railway Deployment Guide - 100% FREE (No Card!)

Railway is the **best free option** - gives you $5/month credit **without asking for credit card!**

## ⚡ Super Quick Deploy (5 Minutes)

### Method 1: One-Click Deploy (EASIEST)

1. **Go to Railway**: https://railway.app/new
2. **Login with GitHub** (no card needed!)
3. **Click "Deploy from GitHub repo"**
4. **Select**: `ShawnTheCreator/kernalagent`
5. **Railway auto-detects** your Dockerfile and builds everything!

That's it! 🎉

---

## 📋 What You Get FREE:

- ✅ **$5 credit/month** (resets monthly)
- ✅ **NO credit card required**
- ✅ **No sleep/cold starts** (unlike Render)
- ✅ **512MB RAM per service**
- ✅ **Unlimited deploys**
- ✅ **Free SSL & custom domains**

**$5 is enough for all 3 services running 24/7!**

---

## 🎯 Step-by-Step Deployment

### Step 1: Sign Up

1. Go to https://railway.app
2. Click "Start a New Project"
3. Login with **GitHub** (recommended)
4. ✅ You instantly get $5 credit!

### Step 2: Deploy Backend

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose: `ShawnTheCreator/kernalagent`
4. Railway detects `Backend/KernalAgentBackend/Dockerfile`
5. Click **"Add Variables"** and paste:

```
ASPNETCORE_URLS=http://0.0.0.0:8080
ASPNETCORE_HTTP_PORTS=8080
ASPNETCORE_ENVIRONMENT=Production
DOTNET_RUNNING_IN_CONTAINER=true
PORT=8080
JWT_KEY=7OKf90gcFyat4Bmh2uekUGjwqxMCTW1Anr5QJvzN6sXVbo8iEl3LdHPSRYIpZD
JWT_ISSUER=KernalAgentBackend
JWT_AUDIENCE=KernalAgentFrontend
CORS_ALLOWED_ORIGINS=https://your-frontend.railway.app
```

6. Add Firebase: `GOOGLE_CREDENTIALS_JSON` (paste full JSON)
7. Click **"Deploy"**

### Step 3: Deploy Microservice

1. Click **"New"** → **"GitHub Repo"**
2. Choose: `ShawnTheCreator/kernalagent`
3. Select: `Microservice/Dockerfile`
4. Add variables:

```
GEMINI_API_KEY=AIzaSyA5BQ4m139k3wiRk56UlUEpSFrryYsc4uY
HOST=0.0.0.0
PORT=8000
MODEL_ID=gemini-2.5-flash
```

5. Click **"Deploy"**

### Step 4: Deploy Frontend

1. Click **"New"** → **"GitHub Repo"**
2. Choose: `ShawnTheCreator/kernalagent`
3. Railway auto-detects Next.js!
4. Add variables:

```
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://your-backend.railway.app/api
NEXT_PUBLIC_WS_URL=wss://your-microservice.railway.app/ws/stream
```

5. Click **"Deploy"**

---

## 🔗 After Deployment

Railway gives each service a URL like:
- Backend: `https://kernalagent-backend-production.up.railway.app`
- Microservice: `https://microservice-production.up.railway.app`
- Frontend: `https://frontend-production.up.railway.app`

**Update the environment variables with real URLs and redeploy!**

---

## 💰 Cost Breakdown (FREE!)

**Example usage:**
- Backend: ~$1.50/month
- Microservice: ~$1.50/month  
- Frontend: ~$1.00/month
- **Total: ~$4/month** (within $5 free credit!)

**You won't pay anything!** ✅

---

## 🆚 Railway vs Render

| Feature | Railway (FREE) | Render (FREE) |
|---------|----------------|---------------|
| Credit Card | ❌ Not required | ⚠️ Required |
| Free Credit | $5/month | None |
| Cold Starts | ❌ No | ✅ Yes (15min) |
| RAM | 512MB | 512MB |
| Deployment | Super easy | Harder |
| Custom domains | ✅ Free | ✅ Free |

**Railway is clearly better for free tier!**

---

## 🚀 Even Faster: Use Railway Template

Railway has deployment templates! Click this to deploy instantly:

**Backend:** https://railway.app/template
- Search for "dotnet" or "ASP.NET"
- Use your repo instead

---

## 🛠️ Using Railway CLI (Optional)

If you want to deploy via command line:

```powershell
# Install Railway CLI
npm install -g @railway/cli

# Or via Scoop
scoop install railway

# Login
railway login

# Link to project
railway link

# Deploy
cd Backend/KernalAgentBackend
railway up
```

---

## 📊 Monitor Usage

1. Go to Railway dashboard
2. Click **"Usage"** tab
3. See your $5 credit and how much you've used
4. Railway shows real-time cost estimates!

---

## ❓ FAQ

**Q: Do I really not need a card?**
A: Correct! Railway gives $5 free credit with just GitHub login.

**Q: What happens after $5?**
A: Your services stop until next month OR you add a card. But 3 small services rarely exceed $5!

**Q: Can I get more free credit?**
A: Yes! Verify your account (still no card) for more credit.

**Q: Is Railway reliable?**
A: Yes! Used by thousands of developers. Better uptime than Render free tier.

---

## 🎁 Pro Tips

1. **Use GitHub for auth** - fastest way
2. **Monitor your usage** - Railway shows real-time costs
3. **Set up alerts** - get notified if you approach $5
4. **Deploy from GitHub** - auto-deploys on push!

---

## ✅ Ready to Deploy?

**Just run:**
```powershell
.\deploy-to-railway.ps1
```

Or manually:
1. Go to https://railway.app/new
2. Login with GitHub
3. Deploy from repo
4. Done! 🚀

**No credit card. No tricks. Actually free.** ✨
