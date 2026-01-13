# 🌐 ngrok Remote Testing Guide

## Step-by-Step: Share Python Server with Teammate

---

## 📍 YOUR SIDE (India - Python Server)

### Step 1: Install ngrok
```powershell
# Option A: Using winget
winget install ngrok

# Option B: Download from https://ngrok.com/download
# Extract and add to PATH
```

### Step 2: Create ngrok Account (Free)
1. Go to https://ngrok.com
2. Sign up (free)
3. Copy your authtoken from dashboard

### Step 3: Configure ngrok
```powershell
ngrok config add-authtoken YOUR_AUTH_TOKEN_HERE
```

### Step 4: Start Your Python Server
```powershell
cd kernalagent-contrib\Microservice
.\venv\Scripts\activate
python standalone_agent_server.py

# Should show: Uvicorn running on http://0.0.0.0:8000
```

### Step 5: Start ngrok Tunnel (New Terminal)
```powershell
ngrok http 8000
```

You'll see something like:
```
Session Status    online
Forwarding        https://abc123xyz.ngrok.io -> http://localhost:8000
```

### Step 6: Share the URL
Copy the `https://abc123xyz.ngrok.io` URL and send to teammate.

---

## 📍 TEAMMATE'S SIDE (South Africa - C# Client)

### Step 1: Update the URL
In `AgentConnectionTest.cs`, change:
```csharp
// FROM:
private static readonly string BASE_URL = "http://localhost:8000";

// TO:
private static readonly string BASE_URL = "https://abc123xyz.ngrok.io";
```

### Step 2: Test Connection
```csharp
bool success = await AgentConnectionTest.TestConnectionAsync();
```

### Step 3: Or Test with PowerShell
```powershell
# Health check
Invoke-RestMethod -Uri "https://abc123xyz.ngrok.io/health"

# Test command
Invoke-RestMethod -Uri "https://abc123xyz.ngrok.io/api/agent/plan" `
  -Method POST -ContentType "application/json" `
  -Body '{"command": "open notepad"}'
```

---

## ✅ Success Checklist

| Step | Your Side (India) | Teammate (SA) |
|------|-------------------|---------------|
| 1 | Python server running | - |
| 2 | ngrok tunnel active | - |
| 3 | Share ngrok URL | Receives URL |
| 4 | - | Updates BASE_URL |
| 5 | See requests in terminal | Sees response |

---

## 🐛 Troubleshooting

**"Connection refused"**
→ Is ngrok still running? URL expires when ngrok stops.

**"Tunnel not found"**
→ The URL changes each time ngrok restarts. Share new URL.

**"502 Bad Gateway"**
→ Python server crashed. Restart it.

---

## 💡 Tips

- ngrok free tier: 1 tunnel, URL changes each restart
- Keep both terminals open (Python server + ngrok)
- Watch Python terminal for incoming requests
