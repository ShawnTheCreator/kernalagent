# Railway Deployment Script - NO CREDIT CARD REQUIRED!
# Railway gives you $5/month FREE credit without asking for card details

Write-Host "Railway Deployment Helper - 100% FREE, No Card Required!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Railway CLI is installed
$railwayInstalled = $null -ne (Get-Command "railway" -ErrorAction SilentlyContinue)

if (-not $railwayInstalled) {
    Write-Host "[STEP 1] Installing Railway CLI..." -ForegroundColor Yellow
    Write-Host ""
    
    # Install Railway CLI via npm
    $npmInstalled = $null -ne (Get-Command "npm" -ErrorAction SilentlyContinue)
    
    if ($npmInstalled) {
        Write-Host "Installing Railway CLI with npm..." -ForegroundColor Cyan
        npm install -g @railway/cli
        Write-Host "[OK] Railway CLI installed!" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Node.js/npm not found. Installing Railway manually..." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Please download and install Railway CLI:" -ForegroundColor Cyan
        Write-Host "Windows: https://railway.app/cli" -ForegroundColor White
        Write-Host ""
        Write-Host "Or install via Scoop:" -ForegroundColor Cyan
        Write-Host "  scoop install railway" -ForegroundColor White
        Write-Host ""
        
        Write-Host "Opening Railway CLI download page..." -ForegroundColor Yellow
        Start-Process "https://railway.app/cli"
        
        Write-Host ""
        Write-Host "After installing, run this script again!" -ForegroundColor Green
        exit 0
    }
}

Write-Host ""
Write-Host "[STEP 2] Login to Railway..." -ForegroundColor Yellow
Write-Host ""
Write-Host "This will open your browser to login (GitHub account recommended)" -ForegroundColor Cyan
Write-Host "NO CREDIT CARD REQUIRED - You get `$5 free credit automatically!" -ForegroundColor Green
Write-Host ""

# Login to Railway
railway login

Write-Host ""
Write-Host "[STEP 3] Creating Railway Project..." -ForegroundColor Yellow
Write-Host ""

# Initialize project
railway init

Write-Host ""
Write-Host "[OK] Railway project created!" -ForegroundColor Green
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS - Deploy Your Services" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[OPTION 1] ONE-CLICK DEPLOY (Easiest):" -ForegroundColor Yellow
Write-Host "  1. Go to: https://railway.app/new" -ForegroundColor White
Write-Host "  2. Click 'Deploy from GitHub repo'" -ForegroundColor White
Write-Host "  3. Select: ShawnTheCreator/kernalagent" -ForegroundColor White
Write-Host "  4. Railway auto-detects Dockerfile and deploys!" -ForegroundColor White
Write-Host ""

Write-Host "[OPTION 2] CLI DEPLOY (Advanced):" -ForegroundColor Yellow
Write-Host "  Run these commands:" -ForegroundColor White
Write-Host "    cd Backend/KernalAgentBackend" -ForegroundColor Gray
Write-Host "    railway up" -ForegroundColor Gray
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "COST: `$0 (FREE)" -ForegroundColor Green
Write-Host "You get `$5 credit/month - enough for all 3 services!" -ForegroundColor Green
Write-Host "No credit card required!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Open Railway dashboard now? (Y/N)" -ForegroundColor Cyan
$openDashboard = Read-Host

if ($openDashboard -eq "Y" -or $openDashboard -eq "y") {
    Start-Process "https://railway.app/new"
    Write-Host "[OK] Opening Railway dashboard..." -ForegroundColor Green
}

Write-Host ""
Write-Host "For full guide, see: RAILWAY_DEPLOY.md" -ForegroundColor Yellow
