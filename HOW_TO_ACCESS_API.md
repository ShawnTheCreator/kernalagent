# How to Access the Backend API

## The 404 Error is Normal!

The backend is an **API**, not a website. There's no page at the root URL (`/`), which is why you see a 404.

## Available Endpoints

### Root Endpoint (After restart)
- **GET** `http://localhost:5042/` - Shows API information and available endpoints

### Authentication Endpoints
- **POST** `http://localhost:5042/api/auth/signup` - Create new account
- **POST** `http://localhost:5042/api/auth/login` - Login
- **GET** `http://localhost:5042/api/auth/me` - Get current user (requires auth token)

### Dashboard Endpoints (Require Authentication)
- **GET** `http://localhost:5042/api/dashboard/skills` - Get skills list
- **GET** `http://localhost:5042/api/dashboard/activities` - Get activities
- **GET** `http://localhost:5042/api/dashboard/metrics` - Get metrics
- **GET** `http://localhost:5042/api/dashboard/stats` - Get stats

### OpenAPI Documentation
- **GET** `http://localhost:5042/openapi/v1.json` - OpenAPI specification

## How to Test

### 1. Stop the Backend
Press `Ctrl+C` in the terminal where backend is running

### 2. Rebuild and Restart
```powershell
cd Backend\KernalAgentBackend
dotnet build
dotnet run
```

### 3. Test the Root Endpoint
Open in browser: `http://localhost:5042/`

You should see JSON with API information!

### 4. Test Signup (using PowerShell)
```powershell
$body = @{
    name = "Test User"
    email = "test@example.com"
    password = "test123"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5042/api/auth/signup" -Method Post -Body $body -ContentType "application/json"
```

### 5. Test Login
```powershell
$body = @{
    email = "test@example.com"
    password = "test123"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:5042/api/auth/login" -Method Post -Body $body -ContentType "application/json"
$token = $response.token
Write-Host "Token: $token"
```

## Using the Desktop App

The desktop app will automatically connect to `http://localhost:5042/api` when you run it. You don't need to access the browser - just use the desktop app's login dialog!

## Quick Test Checklist

- [ ] Backend is running (see "Now listening on..." message)
- [ ] Open `http://localhost:5042/` - Should show API info
- [ ] Open `http://localhost:5042/openapi/v1.json` - Should show OpenAPI spec
- [ ] Run desktop app - Should show login dialog
- [ ] Create account in desktop app - Should work!

