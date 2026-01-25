# 🧠 YOUR INSTRUCTIONS (Python Brain Side)
## Super Simple Steps to Start the AI Brain

---

## 🚀 Step 1: Open PowerShell

Click the **Start Menu** → Type **PowerShell** → Click it

---

## 🚀 Step 2: Go to the Project Folder

Copy and paste this:
```
cd C:\Users\anime\Downloads\ghost-ai---cognitive-desktop-copilot\kernalagent-contrib\Microservice
```
Press **Enter**

---

## 🚀 Step 3: Turn On the Python Environment

Copy and paste this:
```
.\venv\Scripts\activate
```
Press **Enter**

You should see `(venv)` at the start of the line 👍

---

## 🚀 Step 4: Start the AI Brain

Copy and paste this:
```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Press **Enter**

Wait until you see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

🎉 **Done! The AI Brain is now running!**

---

## ✅ How to Check if It's Working

Open a **new PowerShell window** and paste:
```
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

If you see `status: alive` → **It works! 🎉**

---

## ☁️ Deploy to Render (Recommended!)

Instead of running locally, deploy to Render for a permanent URL.

### Step A: Go to https://render.com → Sign up/Login

### Step B: Click "New +" → "Web Service"

### Step C: Connect your GitHub repo (`kernalagent`)

### Step D: Configure:
- **Root Directory:** `Microservice`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment:** Python 3.12

### Step E: Add Environment Variables
```
GOOGLE_API_KEY=your-gemini-key
```

### Step F: Click Deploy!

You'll get a URL like: `https://kernal-agent-brain.onrender.com`

**Send this URL to teammate!** 🎉

---

## ⏹️ How to Stop (Local Only)

Press **Ctrl + C** in the PowerShell window

---

## 🆘 Problems?

| Problem | Fix |
|---------|-----|
| `venv not found` | Run: `python3.12.exe -m venv venv` |
| `module not found` | Run: `pip install -r requirements.txt` |
| `port in use` | Change 8000 to 8001 |
