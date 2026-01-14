# 🖥️ TEAMMATE INSTRUCTIONS (C# Desktop Side)
## Super Simple Steps to Test the Desktop Agent

---

## 🚀 Step 1: Open Visual Studio

Double-click the solution file:
```
Desktop-App\Kernel Agent\Kernel Agent.slnx
```

---

## 🚀 Step 2: Check the Backend URL

Open this file:
```
Services\VoiceToActionService.cs
```

Find line 14 and make sure it says:
```csharp
private readonly string _pythonBackendUrl = "https://YOUR-RENDER-URL.onrender.com/api/agent/plan";
```

**Replace `YOUR-RENDER-URL` with the real URL!**

---

## 🚀 Step 3: Build the App

Press **Ctrl + Shift + B** (or click Build → Build Solution)

Wait for it to say: `Build succeeded`

---

## 🚀 Step 4: Run the App

Press **F5** (or click the green Play button)

The Desktop App will open! 🎉

---

## ✅ Step 5: Test It!

### Test A: Voice Command
1. Click the **microphone button**
2. Say: **"Open Notepad"**
3. Watch if Notepad opens!

### Test B: Quick Connection Test
Add this code somewhere (like a button click):
```csharp
bool success = await AgentConnectionTest.TestConnectionAsync();
```

Check **Output Window** for results.

---

## 📋 What Should Happen

| You Say | App Does |
|---------|----------|
| "Open Notepad" | Opens Notepad |
| "Open Chrome" | Opens Chrome browser |
| "Search for weather" | Opens Google search |
| "Type hello world" | Types "hello world" |

---

## 🆘 Problems?

| Problem | Fix |
|---------|-----|
| Build fails | Check if .NET 8.0 SDK is installed |
| Connection error | Is the backend URL correct? |
| 404 error | URL should end with `/api/agent/plan` |
| Nothing happens | Check Debug Output window for errors |

---

## 🧪 Manual API Test (No App Needed)

Open PowerShell and paste:
```powershell
Invoke-RestMethod -Uri "https://YOUR-RENDER-URL.onrender.com/health"
```

If you see `status: alive` → Backend is working!

Then test a command:
```powershell
Invoke-RestMethod -Uri "https://YOUR-RENDER-URL.onrender.com/api/agent/plan" -Method POST -ContentType "application/json" -Body '{"command": "open notepad"}'
```

You should see: `action: open_app, target: notepad.exe`

---

## ✅ Success Checklist

- [ ] Backend URL is correct in VoiceToActionService.cs
- [ ] App builds without errors
- [ ] Health check returns "alive"
- [ ] Voice command "Open Notepad" works

**All checked? 🎉 Integration Complete!**
