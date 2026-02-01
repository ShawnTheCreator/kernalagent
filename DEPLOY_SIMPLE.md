# 🚀 Super Simple Render Deployment (5 Steps)

Don't worry! I'll guide you through this. Follow these steps **exactly**:

---

## ⚡ BEFORE YOU START

**You need 2 things:**
1. **Gemini API Key** - Get it here: https://aistudio.google.com/app/apikey
2. **Render Account** - Sign up here: https://render.com (free tier is fine!)

---

## 🎯 STEP 1: Run the Magic Script

Open PowerShell in your project folder and run:

```powershell
.\deploy-to-render.ps1
```

**What it does:**
- ✅ Checks your setup
- ✅ Generates secure JWT key
- ✅ Asks for your Gemini API key
- ✅ Creates a file with all environment variables
- ✅ Commits your code to Git
- ✅ Opens Render dashboard for you

**Just answer the questions it asks!**

---

## 🎯 STEP 2: Push to GitHub (if needed)

If you haven't already, create a GitHub repository:

1. Go to https://github.com/new
2. Name it: `kernal-agent`
3. Click "Create repository"
4. Copy the commands it shows and run them:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/kernal-agent.git
git push -u origin main
```

---

## 🎯 STEP 3: Deploy with Render Blueprint

1. **Go to Render**: https://dashboard.render.com
2. **Click** "New" → "Blueprint"
3. **Connect** your GitHub account (first time only)
4. **Select** your repository: `kernal-agent`
5. **Render finds** `render.yaml` automatically
6. **Click** "Apply"

---

## 🎯 STEP 4: Add Secret Keys

Render will ask for these:

### Backend Service:
1. Click "Edit" next to Backend
2. Go to "Environment" tab
3. Find `GOOGLE_CREDENTIALS_JSON`
4. Open your file: `kernal-39125-firebase-adminsdk-fbsvc-4fd56483e9.json`
5. Copy **everything** inside
6. Paste it into the value field
7. **Click Save**

### Microservice:
Already set by the script! ✅

### Frontend:
Already set by the script! ✅

---

## 🎯 STEP 5: Update URLs (After Deployment)

**After all services are deployed** (wait ~10 minutes):

1. **Copy the URLs** Render gives you:
   - Backend: `https://kernalagent-backend-xxxx.onrender.com`
   - Microservice: `https://kernalagent-microservice-xxxx.onrender.com`
   - Frontend: `https://kernalagent-frontend-xxxx.onrender.com`

2. **Update Backend**:
   - Go to Backend service → Environment
   - Find `CORS_ALLOWED_ORIGINS`
   - Change to: `https://kernalagent-frontend-xxxx.onrender.com` (use YOUR URL)
   - Click "Save"

3. **Update Frontend**:
   - Go to Frontend service → Environment
   - Find `NEXT_PUBLIC_API_URL`
   - Change to: `https://kernalagent-backend-xxxx.onrender.com/api`
   - Find `NEXT_PUBLIC_WS_URL`
   - Change to: `wss://kernalagent-microservice-xxxx.onrender.com/ws/stream`
   - Click "Save"

4. **Redeploy** (click "Manual Deploy" on each service)

---

## ✅ TEST IT!

Visit your frontend URL: `https://kernalagent-frontend-xxxx.onrender.com`

You should see your app! 🎉

---

## 😰 STUCK? Common Issues:

### "I don't see render.yaml"
- Run the deploy script first: `.\deploy-to-render.ps1`
- It creates all necessary files

### "Service won't start"
- Check the logs in Render dashboard
- Make sure you added the Firebase JSON correctly
- Verify your Gemini API key is correct

### "CORS error in browser"
- Make sure you updated CORS_ALLOWED_ORIGINS with the EXACT frontend URL
- No trailing slash!
- Redeploy backend after changing

### "Can't push to GitHub"
- Run: `git config --global user.email "your@email.com"`
- Run: `git config --global user.name "Your Name"`
- Try pushing again

---

## 🆘 NEED MORE HELP?

1. Check the logs in Render dashboard (click "Logs" tab)
2. Read the full guide: `RENDER_COMPLETE_GUIDE.md`
3. Ask me! Tell me what error you're seeing

---

## 📋 QUICK CHECKLIST

- [ ] Run `.\deploy-to-render.ps1`
- [ ] Push code to GitHub
- [ ] Create Blueprint in Render
- [ ] Add Firebase JSON to Backend
- [ ] Wait for deployment (~10 min)
- [ ] Copy all service URLs
- [ ] Update CORS_ALLOWED_ORIGINS in Backend
- [ ] Update API URLs in Frontend
- [ ] Redeploy all services
- [ ] Test your app!

---

**You got this! 💪 Just follow the steps one by one.**
