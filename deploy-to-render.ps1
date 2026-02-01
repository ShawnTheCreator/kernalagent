# Automated Render Deployment Helper
# This script guides you through deploying to Render step-by-step

Write-Host "Kernal Agent - Render Deployment Helper" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if a command exists
function Test-Command($command) {
    $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
}

# Function to generate JWT key
function New-JWTKey {
    return -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
}

# Step 1: Check prerequisites
Write-Host "[Step 1] Checking Prerequisites..." -ForegroundColor Yellow
Write-Host ""

$gitInstalled = Test-Command "git"
$hasGitRepo = Test-Path ".git"

if (-not $gitInstalled) {
    Write-Host "[ERROR] Git is not installed. Please install from: https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

if (-not $hasGitRepo) {
    Write-Host "[ERROR] This is not a Git repository. Please run: git init" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Git is installed and repository is initialized" -ForegroundColor Green
Write-Host ""

# Step 2: Collect API Keys
Write-Host "[Step 2] Collecting API Keys..." -ForegroundColor Yellow
Write-Host ""

# Generate JWT Key
$jwtKey = New-JWTKey
Write-Host "[OK] Generated JWT Key (64 characters)" -ForegroundColor Green
Write-Host ""

# Ask for Gemini API Key
Write-Host "We need your Gemini API Key from Google AI Studio" -ForegroundColor Cyan
Write-Host "Get it here: https://aistudio.google.com/app/apikey" -ForegroundColor Gray
$geminiKey = Read-Host "Enter your Gemini API Key (starts with AIza)"

if ([string]::IsNullOrWhiteSpace($geminiKey) -or -not $geminiKey.StartsWith("AIza")) {
    Write-Host "[ERROR] Invalid Gemini API Key. It should start with 'AIza'" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Gemini API Key validated" -ForegroundColor Green
Write-Host ""

# Check for Firebase credentials
Write-Host "Checking for Firebase credentials..." -ForegroundColor Cyan
$firebaseFile = "kernal-39125-firebase-adminsdk-fbsvc-4fd56483e9.json"

if (Test-Path $firebaseFile) {
    Write-Host "[OK] Found Firebase credentials file: $firebaseFile" -ForegroundColor Green
    $firebaseJson = Get-Content $firebaseFile -Raw
} else {
    Write-Host "[WARNING] Firebase credentials file not found" -ForegroundColor Yellow
    Write-Host "You'll need to add this manually in Render dashboard later" -ForegroundColor Gray
    $firebaseJson = ""
}
Write-Host ""

# Step 3: Create environment variables file for reference
Write-Host "[Step 3] Creating Environment Variables Reference..." -ForegroundColor Yellow
Write-Host ""

$envVarsContent = @"
# RENDER ENVIRONMENT VARIABLES
# Copy these to your Render dashboard for each service

# ============================================
# BACKEND SERVICE
# ============================================
ASPNETCORE_URLS=http://0.0.0.0:8080
ASPNETCORE_HTTP_PORTS=8080
ASPNETCORE_ENVIRONMENT=Production
DOTNET_RUNNING_IN_CONTAINER=true
PORT=8080
JWT_KEY=$jwtKey
JWT_ISSUER=KernalAgentBackend
JWT_AUDIENCE=KernalAgentFrontend
CORS_ALLOWED_ORIGINS=https://kernalagent-frontend.onrender.com
# Add this manually after getting the exact frontend URL

# Firebase credentials - ADD MANUALLY IN RENDER
# GOOGLE_CREDENTIALS_JSON=<paste your Firebase JSON here>

# ============================================
# MICROSERVICE
# ============================================
GEMINI_API_KEY=$geminiKey
HOST=0.0.0.0
PORT=8000
MODEL_ID=gemini-2.5-flash

# ============================================
# FRONTEND
# ============================================
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://kernalagent-backend.onrender.com/api
NEXT_PUBLIC_WS_URL=wss://kernalagent-microservice.onrender.com/ws/stream
# Update these after deployment with actual URLs

"@

$envVarsContent | Out-File -FilePath "RENDER_ENV_VARS.txt" -Encoding UTF8

Write-Host "[OK] Created RENDER_ENV_VARS.txt with all your environment variables" -ForegroundColor Green
Write-Host ""

# Step 4: Check if code is committed
Write-Host "[Step 4] Checking Git Status..." -ForegroundColor Yellow
Write-Host ""

$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "[WARNING] You have uncommitted changes. Committing now..." -ForegroundColor Yellow
    git add .
    git commit -m "Configure for Render deployment"
    Write-Host "[OK] Changes committed" -ForegroundColor Green
} else {
    Write-Host "[OK] All changes are committed" -ForegroundColor Green
}
Write-Host ""

# Step 5: Check for GitHub remote
Write-Host "[Step 5] Checking GitHub Remote..." -ForegroundColor Yellow
Write-Host ""

$remote = git remote -v | Select-String "origin"
if ($remote) {
    Write-Host "[OK] GitHub remote is configured:" -ForegroundColor Green
    Write-Host $remote -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "Do you want to push to GitHub now? (Y/N)" -ForegroundColor Cyan
    $pushChoice = Read-Host
    
    if ($pushChoice -eq "Y" -or $pushChoice -eq "y") {
        Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
        git push origin main
        Write-Host "[OK] Pushed to GitHub" -ForegroundColor Green
    }
} else {
    Write-Host "[WARNING] No GitHub remote found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To add GitHub remote, run:" -ForegroundColor Gray
    Write-Host "  git remote add origin https://github.com/yourusername/your-repo.git" -ForegroundColor Gray
    Write-Host "  git push -u origin main" -ForegroundColor Gray
}
Write-Host ""

# Step 6: Summary and Next Steps
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SETUP COMPLETE! Next Steps:" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[STEP 1] OPEN RENDER:" -ForegroundColor Yellow
Write-Host "   Go to https://dashboard.render.com" -ForegroundColor White
Write-Host ""

Write-Host "[STEP 2] CREATE BLUEPRINT DEPLOYMENT:" -ForegroundColor Yellow
Write-Host "   - Click 'New' -> 'Blueprint'" -ForegroundColor White
Write-Host "   - Connect your GitHub repository" -ForegroundColor White
Write-Host "   - Select 'render.yaml' from root directory" -ForegroundColor White
Write-Host ""

Write-Host "[STEP 3] SET ENVIRONMENT VARIABLES:" -ForegroundColor Yellow
Write-Host "   - Open: RENDER_ENV_VARS.txt (created in this folder)" -ForegroundColor White
Write-Host "   - Copy variables for each service in Render dashboard" -ForegroundColor White
Write-Host ""

Write-Host "[STEP 4] ADD FIREBASE CREDENTIALS:" -ForegroundColor Yellow
if ($firebaseJson) {
    Write-Host "   - Backend service -> Environment" -ForegroundColor White
    Write-Host "   - Add variable: GOOGLE_CREDENTIALS_JSON" -ForegroundColor White
    Write-Host "   - Paste content from: $firebaseFile" -ForegroundColor White
} else {
    Write-Host "   [WARNING] You need to get Firebase credentials first" -ForegroundColor Red
}
Write-Host ""

Write-Host "[STEP 5] CLICK 'APPLY' TO DEPLOY!" -ForegroundColor Yellow
Write-Host "   Render will build and deploy all services" -ForegroundColor White
Write-Host ""

Write-Host "[STEP 6] UPDATE URLS:" -ForegroundColor Yellow
Write-Host "   After deployment, update these in Render:" -ForegroundColor White
Write-Host "   - Backend: CORS_ALLOWED_ORIGINS with actual frontend URL" -ForegroundColor White
Write-Host "   - Frontend: NEXT_PUBLIC_API_URL with actual backend URL" -ForegroundColor White
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FILES TO REFERENCE:" -ForegroundColor Cyan
Write-Host "  - RENDER_ENV_VARS.txt - Your environment variables" -ForegroundColor White
Write-Host "  - RENDER_COMPLETE_GUIDE.md - Full deployment guide" -ForegroundColor White
Write-Host "  - render.yaml - Blueprint configuration" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "You're ready to deploy! Follow the steps above." -ForegroundColor Green
Write-Host ""

# Open Render dashboard in browser
Write-Host "Open Render dashboard in browser now? (Y/N)" -ForegroundColor Cyan
$openBrowser = Read-Host

if ($openBrowser -eq "Y" -or $openBrowser -eq "y") {
    Start-Process "https://dashboard.render.com"
    Write-Host "[OK] Opening Render dashboard..." -ForegroundColor Green
}

Write-Host ""
Write-Host "Need help? Check RENDER_COMPLETE_GUIDE.md for detailed instructions!" -ForegroundColor Yellow
