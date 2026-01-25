# C# Desktop Agent ↔ Python Microservice Integration Guide

> **For:** C# Desktop App Developer  
> **Purpose:** Enable command execution from Desktop Agent to Python Brain  
> **Date:** 2026-01-13

---

## 🎯 Goal

Test that the C# Desktop Agent can send commands to the Python Microservice and receive action plans.

---

## 📐 Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                         USER SPEAKS                                 │
│                     "Open Notepad and type hello"                   │
└─────────────────────────────────┬──────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│               C# DESKTOP AGENT (The Executor)                       │
│  ┌──────────────────┐                                               │
│  │ VoiceToAction    │  POST /api/agent/plan                         │
│  │ Service          │  {"command": "Open Notepad and type hello"}   │
│  └────────┬─────────┘                                               │
│           │                                                         │
└───────────┼─────────────────────────────────────────────────────────┘
            │ HTTP
            ▼
┌────────────────────────────────────────────────────────────────────┐
│             PYTHON MICROSERVICE (The Brain)                         │
│         http://localhost:8000                                       │
│                                                                     │
│  Parses command → Returns action steps                              │
│                                                                     │
│  Response: [                                                        │
│    {"action": "open_app", "target": "notepad.exe"},                 │
│    {"action": "type_text", "content": "hello"}                      │
│  ]                                                                  │
└─────────────────────────────────┬──────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│               C# DESKTOP AGENT (Executes Actions)                   │
│  ┌──────────────────┐                                               │
│  │ WindowsAutomation│  OpenApplication("notepad.exe")               │
│  │                  │  TypeIntoApp("hello")                         │
│  └──────────────────┘                                               │
└────────────────────────────────────────────────────────────────────┘
```

---

## ✅ Prerequisites

### Python Side (Already Done)
```bash
cd kernalagent-contrib/Microservice
.\venv\Scripts\activate
python standalone_agent_server.py

# Should see:
# 🧠 Kernal Agent - Desktop Integration Server
# Uvicorn running on http://0.0.0.0:8000
```

### C# Side (Your Part)
- Visual Studio 2022 or later
- .NET 8.0 SDK
- NuGet packages: `System.Net.Http`, `System.Text.Json`

---

## 🔧 Step 1: Verify Python Server is Running

Open PowerShell and test:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET
# Expected: {"status":"ready","version":"1.0.0"}
```

Test the plan endpoint:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/agent/plan" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"command": "open notepad"}' | ConvertTo-Json

# Expected:
# {
#     "session_id":  "...",
#     "steps":  [{"action": "open_app", "target": "notepad.exe", ...}],
#     "schema_version":  "1.0.0"
# }
```

---

## 🔧 Step 2: Check Current C# Implementation

The existing code in `VoiceToActionService.cs` already has the HTTP call:

```csharp
// Line 14: Current endpoint
private readonly string _pythonBackendUrl = "http://localhost:8000/api/agent/plan";

// Line 45-54: HTTP POST to get action plan
private async Task<JsonElement[]> GetActionPlanFromPython(string userCommand)
{
    using var client = new HttpClient();
    var requestBody = new { command = userCommand };
    var content = new StringContent(JsonSerializer.Serialize(requestBody), Encoding.UTF8, "application/json");
    var response = await client.PostAsync(_pythonBackendUrl, content);
    // ... parses response
}
```

---

## 🧪 Step 3: Create Minimal Test

Create a new file `Services/AgentConnectionTest.cs`:

```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace Kernel_Agent.Services
{
    public static class AgentConnectionTest
    {
        private static readonly string BACKEND_URL = "http://localhost:8000/api/agent/plan";
        
        /// <summary>
        /// Test connection to Python Microservice.
        /// Call this from a button click or on app startup.
        /// </summary>
        public static async Task<bool> TestConnectionAsync()
        {
            try
            {
                using var client = new HttpClient();
                client.Timeout = TimeSpan.FromSeconds(10);
                
                // 1. Health check
                var healthResponse = await client.GetAsync("http://localhost:8000/health");
                if (!healthResponse.IsSuccessStatusCode)
                {
                    System.Diagnostics.Debug.WriteLine("[AGENT TEST] Health check failed!");
                    return false;
                }
                System.Diagnostics.Debug.WriteLine("[AGENT TEST] ✓ Health check passed");
                
                // 2. Test command
                var requestBody = new { command = "open notepad" };
                var json = JsonSerializer.Serialize(requestBody);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                
                var response = await client.PostAsync(BACKEND_URL, content);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[AGENT TEST] ✓ Got response: {responseJson}");
                    return true;
                }
                else
                {
                    System.Diagnostics.Debug.WriteLine($"[AGENT TEST] ✗ Failed: {response.StatusCode}");
                    return false;
                }
            }
            catch (HttpRequestException ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AGENT TEST] ✗ Connection error: {ex.Message}");
                System.Diagnostics.Debug.WriteLine("[AGENT TEST] Is the Python server running?");
                return false;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AGENT TEST] ✗ Error: {ex.Message}");
                return false;
            }
        }
    }
}
```

---

## 🧪 Step 4: Call the Test

Add a test button or call on startup in `MainWindow.xaml.cs`:

```csharp
// In MainWindow constructor or a button click handler:
private async void TestAgentConnection_Click(object sender, RoutedEventArgs e)
{
    bool success = await AgentConnectionTest.TestConnectionAsync();
    
    if (success)
    {
        // Show success dialog or update UI
        System.Diagnostics.Debug.WriteLine("Connection to Python Brain: SUCCESS ✓");
    }
    else
    {
        // Show error dialog
        System.Diagnostics.Debug.WriteLine("Connection to Python Brain: FAILED ✗");
    }
}
```

Or add a quick test in `MainWindow()` constructor:

```csharp
public MainWindow()
{
    InitializeComponent();
    
    // Quick connection test on startup
    _ = Task.Run(async () =>
    {
        await Task.Delay(2000); // Wait for window to load
        await AgentConnectionTest.TestConnectionAsync();
    });
}
```

---

## 📋 API Reference

### Endpoint
```
POST http://localhost:8000/api/agent/plan
Content-Type: application/json
```

### Request Body
```json
{
  "command": "open notepad",
  "session_id": "optional-uuid"
}
```

### Response
```json
{
  "session_id": "586f6db5-4676-43cd-8b74-901be02b42ff",
  "steps": [
    {
      "action": "open_app",
      "target": "notepad.exe",
      "url": null,
      "query": null,
      "content": null
    }
  ],
  "schema_version": "1.0.0"
}
```

### Supported Actions

| Action | Fields Used | Description |
|--------|-------------|-------------|
| `open_app` | `target` | Open an application (e.g., `notepad.exe`) |
| `type_text` | `content` | Type text at current cursor |
| `navigate` | `url` | Navigate to URL in browser |
| `search` | `query` | Search for something |
| `click` | `target` | Click an element (needs coordinates later) |

### Supported Commands

| Command Pattern | Example |
|-----------------|---------|
| `open [app]` | "open notepad", "open chrome", "open vscode" |
| `type [text]` | "type hello world" |
| `search [query]` | "search for weather" |
| `go to [url]` | "go to google.com" |

---

## 🐛 Troubleshooting

### "Connection refused" or timeout
```
[AGENT TEST] ✗ Connection error: No connection could be made...
```
**Fix:** Python server not running. Start it:
```bash
cd kernalagent-contrib/Microservice
.\venv\Scripts\activate
python standalone_agent_server.py
```

### "404 Not Found"
**Fix:** Wrong endpoint URL. Must be `/api/agent/plan` (not `/agent/plan`)

### JSON parsing errors
**Fix:** Ensure proper `Content-Type: application/json` header

---

## ✅ Success Criteria

When the test passes, you should see in Debug Output:
```
[AGENT TEST] ✓ Health check passed
[AGENT TEST] ✓ Got response: {"session_id":"...","steps":[{"action":"open_app",...}],...}
```

---

## 📁 Files Reference

| File | Location |
|------|----------|
| Python Server | `kernalagent-contrib/Microservice/standalone_agent_server.py` |
| C# Voice Service | `Desktop-App/Kernel Agent/Services/VoiceToActionService.cs` |
| C# Automation | `Desktop-App/Kernel Agent/Services/WindowsAutomation.cs` |
| C# Test (create this) | `Desktop-App/Kernel Agent/Services/AgentConnectionTest.cs` |

---

**Questions?** The Python server logs all requests, so check the terminal where it's running to see if requests are arriving.
