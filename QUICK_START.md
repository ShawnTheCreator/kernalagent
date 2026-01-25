# Quick Start Guide

## Fastest Way to Get Running

### 1. Backend Setup (2 minutes)

```powershell
# Navigate to backend
cd "Backend\KernalAgentBackend"

# Create .env file
@"
JWT_KEY=MySuperSecretKey123456789012345678901234567890
JWT_ISSUER=KernalAgentBackend
JWT_AUDIENCE=KernalAgentFrontend
DATABASE_CONNECTION_STRING=
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
"@ | Out-File -FilePath .env -Encoding utf8

# Run backend
dotnet run
```

**Wait for:** `Now listening on: http://localhost:5042`

### 2. Test Backend (1 minute)

Open browser: `https://localhost:7062/swagger`

Try the signup endpoint:
- Click `POST /api/auth/signup` → "Try it out"
- Use this JSON:
```json
{
  "name": "Test User",
  "email": "test@example.com",
  "password": "test123"
}
```
- Click "Execute"
- Copy the token from response

### 3. Desktop App Setup (1 minute)

```powershell
# Navigate to desktop app
cd "Desktop-App\Kernel Agent"

# Create .env file (optional - has defaults)
@"
API_BASE_URL=http://localhost:5042/api
"@ | Out-File -FilePath .env -Encoding utf8
```

### 4. Run Desktop App

**Option A: Visual Studio**
- Open `Kernel Agent.slnx`
- Press F5

**Option B: Command Line**
```powershell
dotnet run --project "Kernel Agent.csproj"
```

### 5. Test Login

When desktop app opens:
1. Login dialog appears
2. Click "Sign Up"
3. Enter:
   - Name: `Test User`
   - Email: `test@example.com`
   - Password: `test123`
4. Click "Sign Up"
5. ✅ You're logged in!

## Common Issues

**Backend error: "JWT_KEY required"**
→ Create `.env` file in `Backend\KernalAgentBackend\`

**Desktop app can't connect**
→ Make sure backend is running on port 5042

**HTTPS certificate error**
→ Run: `dotnet dev-certs https --trust`

## Full Documentation

See `RUN_AND_TEST_GUIDE.md` for detailed instructions.

