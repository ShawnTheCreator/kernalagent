# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**Kernal Agent** is a multimodal AI desktop copilot that combines vision-based reasoning with natural language processing to automate desktop tasks. The system consists of three main components that communicate to provide a seamless user experience:

### Architecture Components

1. **Backend (C# .NET 10)** - Authentication & Data API
   - Location: `Backend/KernalAgentBackend/`
   - Framework: ASP.NET Core with Entity Framework
   - Purpose: JWT authentication, user management, dashboard data
   - Database: InMemory (dev) or SQL Server (production) + Firebase Firestore
   - Auth: JWT Bearer tokens with BCrypt password hashing

2. **Microservice (Python/FastAPI)** - AI Brain
   - Location: `Microservice/`
   - Framework: FastAPI with WebSocket support
   - Purpose: Gemini 2.5 Flash vision processing, natural language understanding, action planning
   - Key features: Real-time vision pipeline, structured action plans (CLICK/TYPE/WAIT), Set-of-Mark UI interpretation
   - Agents: Janitor Agent (autonomous file management), Recovery Agent

3. **Desktop App (C# WinUI 3)** - Native Client
   - Location: `Desktop-App/Kernel Agent/`
   - Framework: WinUI 3 (.NET 8)
   - Purpose: Native Windows desktop application with UI automation capabilities
   - Features: Voice input (Google Speech API), screen capture, system automation, authentication flow

4. **Frontend (Next.js)** - Web Interface
   - Location: `Frontend/`
   - Framework: Next.js 16 with React 19, TypeScript, Tailwind CSS 4
   - Purpose: Landing page, login/signup, dashboard, agent marketplace
   - Features: Animated UI, real-time WebSocket updates, Firebase auth integration

### System Flow

```
User → Desktop App (WinUI) → Microservice (FastAPI/Gemini) → Action Execution
                          ↓
                   Backend (.NET) ← Frontend (Next.js)
                          ↓
                   Firestore/InMemory DB
```

## Common Development Commands

### Backend (.NET API)

**Working Directory:** `Backend/KernalAgentBackend/`

```powershell
# Setup environment (first time)
copy .env.example .env
# Edit .env and set JWT_KEY (minimum 32 chars)

# Restore packages
dotnet restore

# Build
dotnet build

# Run development server
dotnet run
# Backend runs on http://localhost:5042 and https://localhost:7062
# Swagger UI available at https://localhost:7062/swagger (dev only)

# Trust HTTPS certificate (if needed)
dotnet dev-certs https --trust
```

**Important:** Backend requires `JWT_KEY` environment variable. Use PowerShell to generate:
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})
```

### Microservice (Python AI Brain)

**Working Directory:** `Microservice/`

```powershell
# Create virtual environment (first time)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Setup environment
# Create .env file with:
# GEMINI_API_KEY=your_key_starts_with_AIza...

# Run development server
python -m app.main
# Runs on http://localhost:8000

# Run tests
pytest tests/

# Test specific file
pytest tests/test_brain.py
```

**Key endpoints:**
- `POST /api/agent/plan` - v1 planning with Gemini
- `POST /api/agent/plan/v2` - v2 LLM-first planning
- `POST /api/vision/find-target` - Vision-based click targeting
- `GET /health` - Health check
- `ws://localhost:8000/ws/stream` - WebSocket for real-time vision

### Desktop App (WinUI 3)

**Working Directory:** `Desktop-App/Kernel Agent/`

```powershell
# Build
dotnet build

# Run
dotnet run --project "Kernel Agent.csproj"

# Or open in Visual Studio
# Open "Kernel Agent.slnx" and press F5
```

**Note:** Desktop app connects to Backend API at `http://localhost:5042/api` by default. Can be configured via `.env` file with `API_BASE_URL` key.

### Frontend (Next.js)

**Working Directory:** `Frontend/`

```powershell
# Install dependencies (first time)
npm install

# Run development server
npm run dev
# Runs on http://localhost:3000

# Build for production
npm run build

# Start production server
npm run start

# Run linter
npm run lint
```

**Environment variables:** Create `.env.local` with:
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:5042/api)
- `NEXT_PUBLIC_WS_URL` - WebSocket URL (default: ws://localhost:8000/ws/stream)

## Quick Start for Development

### Option 1: Automated Setup

```powershell
# From repository root

# 1. Setup backend
.\setup-backend.ps1

# 2. Start backend
cd Backend\KernalAgentBackend
dotnet run

# 3. Start microservice (new terminal)
cd Microservice
.\venv\Scripts\activate
python -m app.main

# 4. Start frontend (new terminal)
cd Frontend
npm run dev

# 5. Start desktop app (new terminal)
cd "Desktop-App\Kernel Agent"
dotnet run
```

### Option 2: Manual Test Flow

See `QUICK_START.md` for fastest 4-minute setup and testing guide.

## Architecture Details

### Backend Structure

```
Backend/KernalAgentBackend/
├── Controllers/          # API endpoints
│   ├── AuthController.cs       # /api/auth/* - signup, login, me
│   ├── DashboardController.cs  # /api/dashboard/* - skills, activities, metrics, stats
│   └── HomeController.cs       # Root endpoint
├── Data/                # Entity Framework
│   ├── ApplicationDbContext.cs
│   └── DbInitializer.cs
├── DTOs/                # Data transfer objects
├── Models/              # Entity models
└── Program.cs           # App configuration, JWT, CORS, Firestore
```

**Authentication Flow:**
1. User calls `/api/auth/signup` or `/api/auth/login`
2. Backend validates credentials (BCrypt) and checks Firestore
3. JWT token generated with 7-day expiration
4. Token required in `Authorization: Bearer <token>` header for protected routes

### Microservice Structure

```
Microservice/app/
├── main.py              # FastAPI entry point, all routes
├── api/
│   ├── websocket.py     # WebSocket handler for vision stream
│   ├── agent_plan.py    # HTTP planning endpoints
│   ├── agent_routes.py  # Agent preview APIs
│   ├── executor_ws.py   # Hybrid WebSocket executor
│   └── speech_routes.py # Voice transcription
├── engine/
│   └── vision.py        # Gemini vision processing, image compression
├── vision/
│   └── vision_targeting.py  # Click target finding
├── agents/              # Multi-agent system
│   ├── janitor/         # Autonomous file organizer
│   └── recovery/        # Error recovery
├── brain/               # Reasoning engine
├── executor/            # Action execution
└── core/
    ├── config.py        # Environment settings
    └── schemas.py       # Pydantic models
```

**Vision Pipeline:**
1. Desktop app sends base64 screenshot via WebSocket
2. Image compressed to 1024px max dimension (rate limit mitigation)
3. Gemini 2.5 Flash processes with user intent
4. Returns structured JSON: `{action_type: "CLICK", coordinate_label: 42, text_payload: null}`

### Desktop App Structure

```
Desktop-App/Kernel Agent/
├── MainWindow.xaml/cs   # Main application window
├── App.xaml/cs          # Application lifecycle
├── Services/            # Backend communication, auth, automation
├── *.xaml               # UI pages: ForgePage, HistoryPage, MemoryPage, 
│                        # MarketplacePage, SandboxPage, SecurityPage, SettingsPage
└── Assets/              # Images, videos, icons
```

**Key Technologies:**
- WindowsInput - Keyboard/mouse automation
- Google.Cloud.Speech.V1 - Voice recognition
- FirebaseAdmin/Firestore - User data sync
- dotenv.net - Environment configuration

### Frontend Structure

```
Frontend/src/
├── app/                 # Next.js App Router
│   ├── page.tsx         # Landing page
│   ├── login/           # Login page
│   ├── signup/          # Signup page
│   └── dashboard/       # Dashboard with subroutes
│       ├── activity/
│       ├── profile/
│       ├── settings/
│       ├── skills/
│       └── usage/
├── components/
│   ├── ui/              # Reusable components (AuthInput)
│   ├── layout/          # Navbar, Footer, AuthLayout
│   ├── sections/        # Landing sections (Hero, DemoSection, BentoFeatures)
│   ├── effects/         # Visual effects (CursorGlow, LogoWall)
│   └── dashboard/       # Dashboard-specific components
├── hooks/               # useMousePosition, useScrollProgress, useInView
├── stores/              # Zustand state management
└── contexts/            # React contexts
```

## Testing

### Backend Testing

```powershell
# Quick test script
.\test-backend.ps1

# Manual tests via Swagger
# 1. Open https://localhost:7062/swagger
# 2. POST /api/auth/signup with test data
# 3. Copy token from response
# 4. Click "Authorize" and enter "Bearer <token>"
# 5. Test protected endpoints
```

### Microservice Testing

```powershell
cd Microservice

# Run all tests
pytest

# Test WebSocket connection
python tests/test_brain.py

# Test specific agent
pytest app/agents/janitor/tests/
```

### Integration Testing

Full flow test (requires all services running):
1. Backend running on port 5042
2. Microservice running on port 8000
3. Desktop app login → should succeed
4. Desktop app voice command → should execute via microservice
5. Frontend dashboard → should show user data from backend

**Verification checklist:** See `README_TESTING.md` section "Verification Checklist"

## Environment Variables

### Backend (`.env` in `Backend/KernalAgentBackend/`)

```
JWT_KEY=<64-char random string>           # REQUIRED
JWT_ISSUER=KernalAgentBackend
JWT_AUDIENCE=KernalAgentFrontend
DATABASE_CONNECTION_STRING=               # Empty for InMemory
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
GOOGLE_APPLICATION_CREDENTIALS=path/to/firebase-key.json
# OR
GOOGLE_CREDENTIALS_JSON=<full JSON content>  # For cloud deployment
```

### Microservice (`.env` in `Microservice/`)

```
GEMINI_API_KEY=AIza...                    # REQUIRED - Google AI Studio key
HOST=0.0.0.0
PORT=8000
MODEL_ID=gemini-2.5-flash
```

### Desktop App (`.env` in `Desktop-App/Kernel Agent/`)

```
API_BASE_URL=http://localhost:5042/api    # Optional - has default
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

### Frontend (`.env.local` in `Frontend/`)

```
NEXT_PUBLIC_API_URL=http://localhost:5042/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/stream
```

**Security:** Never commit `.env` files. All are in `.gitignore`.

## Key Design Patterns

### Multi-Agent Architecture
The microservice uses a registry-based agent system:
- `JanitorAgent` - Autonomous file organization with capabilities (compress, archive, organize, clean)
- Agents register on startup in `main.py` startup event
- WebSocket notifications for permission requests
- Daemon mode for continuous monitoring of Downloads/Desktop

### WebSocket Communication
Two primary WebSocket endpoints:
1. `/ws/stream` - Vision stream from desktop app to AI brain
2. `/ws/executor` - Hybrid executor for real-time action feedback
3. `/ws/voice` - Continuous voice transcription

Message format:
```json
// Client → Server
{"type": "intent_update", "payload": "Find the Export button"}
{"type": "frame", "image": "base64_screenshot"}

// Server → Client
{"type": "action", "payload": {"action_type": "CLICK", "coordinate_label": 42}}
{"type": "auth_success", "deviceId": "...", "token": "..."}
```

### Vision Targeting with Set-of-Mark
- Desktop app overlays numbered tags on UI elements
- Screenshot sent to microservice with target description
- Gemini identifies correct number/coordinates
- Returns precise pixel coordinates for click execution
- Enables commands like "click on any video" without DOM access

### Firebase Integration
- Backend uses Firestore for persistent user storage
- Desktop app syncs user data via Firebase
- Frontend can use Firebase client SDK or Backend API
- Credentials loaded via `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_CREDENTIALS_JSON`

## Troubleshooting

### Backend won't start
- Verify `.env` exists in `Backend/KernalAgentBackend/`
- Check `JWT_KEY` is set and ≥32 characters
- If certificate error: `dotnet dev-certs https --trust`

### Microservice connection issues
- Ensure `GEMINI_API_KEY` is set
- Check firewall allows port 8000
- Verify Python version ≥3.10

### Desktop app can't connect
- Backend must be running on port 5042
- Check `API_BASE_URL` in desktop app `.env`
- Verify no firewall blocking

### Cross-component authentication
- Desktop app gets token from backend `/api/auth/login`
- Token stored locally for subsequent requests
- Frontend uses same backend API for auth
- WebSocket auth uses polling (`/api/auth/poll`) or real-time sync (`/api/auth/sync`)

## Remote Testing with ngrok

For testing across networks (e.g., between team members):

```powershell
# Developer side (hosting microservice)
ngrok http 8000

# Share the https URL with team
# Teammate updates BASE_URL in their code to ngrok URL
```

See `NGROK_TESTING_GUIDE.md` for detailed instructions.

## Important Notes

### Port Configuration
- Backend HTTP: 5042
- Backend HTTPS: 7062
- Microservice: 8000
- Frontend: 3000

### Platform Specifics
- Desktop app is Windows-only (WinUI 3)
- Backend and Microservice are cross-platform
- Development primarily on Windows (PowerShell scripts)

### Gemini API Rate Limits
- Microservice implements exponential backoff
- Images compressed to 1024px before sending
- Consider caching strategies for repeated frames

### Database Notes
- Development uses InMemory database (data lost on restart)
- Production requires SQL Server connection string
- Firebase Firestore used for user data persistence
- Seed data created on startup (DbInitializer, SeedData)

### CORS Configuration
- Backend allows origins from `CORS_ALLOWED_ORIGINS` env var
- Development mode allows all origins
- Update for production deployment

### HTTPS in Production
- Backend disables HTTPS redirection in containers
- Cloud platforms (Render, etc.) handle HTTPS at load balancer
- Never use `app.UseHttpsRedirection()` in containerized deployments
