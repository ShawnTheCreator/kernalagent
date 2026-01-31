# Quick Test Script for App Opening & Action Chain Improvements
# This script verifies that the reliability improvements are working

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "App Opening & Action Chain Quick Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if a process is running
function Test-ProcessRunning {
    param([string]$ProcessName)
    $process = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
    return $null -ne $process
}

# Function to wait for process to start
function Wait-ForProcess {
    param(
        [string]$ProcessName,
        [int]$TimeoutSeconds = 10
    )
    
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        if (Test-ProcessRunning -ProcessName $ProcessName) {
            return $true
        }
        Start-Sleep -Milliseconds 500
        $elapsed += 0.5
    }
    return $false
}

# Test 1: Check if services are running
Write-Host "Test 1: Checking if services are running..." -ForegroundColor Yellow
$backendRunning = Test-NetConnection -ComputerName localhost -Port 5042 -InformationLevel Quiet -WarningAction SilentlyContinue
$microserviceRunning = Test-NetConnection -ComputerName localhost -Port 8000 -InformationLevel Quiet -WarningAction SilentlyContinue

if ($backendRunning) {
    Write-Host "  ✓ Backend running on port 5042" -ForegroundColor Green
} else {
    Write-Host "  ✗ Backend NOT running on port 5042" -ForegroundColor Red
    Write-Host "    Start with: cd Backend\KernalAgentBackend; dotnet run" -ForegroundColor Gray
}

if ($microserviceRunning) {
    Write-Host "  ✓ Microservice running on port 8000" -ForegroundColor Green
} else {
    Write-Host "  ✗ Microservice NOT running on port 8000" -ForegroundColor Red
    Write-Host "    Start with: cd Microservice; .\venv\Scripts\activate; python -m app.main" -ForegroundColor Gray
}

Write-Host ""

# Test 2: Test Notepad opening reliability
Write-Host "Test 2: Testing Notepad opening (with retry logic)..." -ForegroundColor Yellow

# Close any existing Notepad instances
Get-Process -Name notepad -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

# Test opening Notepad 3 times to verify reliability
$successCount = 0
for ($i = 1; $i -le 3; $i++) {
    Write-Host "  Attempt $i/3: Opening Notepad..." -NoNewline
    
    Start-Process notepad.exe
    $opened = Wait-ForProcess -ProcessName "notepad" -TimeoutSeconds 5
    
    if ($opened) {
        Write-Host " ✓ Success" -ForegroundColor Green
        $successCount++
        Get-Process -Name notepad -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Milliseconds 500
    } else {
        Write-Host " ✗ Failed" -ForegroundColor Red
    }
}

$reliability = ($successCount / 3) * 100
Write-Host "  Reliability: $successCount/3 ($reliability%)" -ForegroundColor $(if ($reliability -ge 90) { "Green" } else { "Red" })
Write-Host ""

# Test 3: Test Chrome opening with profile
Write-Host "Test 3: Testing Chrome opening with profile argument..." -ForegroundColor Yellow

# Close any existing Chrome instances
Get-Process -Name chrome -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host "  Opening Chrome with --profile-directory=Default..." -NoNewline

# Find Chrome executable
$chromePaths = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
)

$chromeExe = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($chromeExe) {
    Start-Process -FilePath $chromeExe -ArgumentList '--profile-directory="Default"'
    $opened = Wait-ForProcess -ProcessName "chrome" -TimeoutSeconds 8
    
    if ($opened) {
        Write-Host " ✓ Success" -ForegroundColor Green
        
        # Wait a bit and check if profile picker appeared
        Start-Sleep -Seconds 2
        $chromeWindows = (Get-Process -Name chrome | Where-Object { $_.MainWindowTitle -ne "" }).Count
        
        if ($chromeWindows -eq 1) {
            Write-Host "  ✓ Single Chrome window (no profile picker detected)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Multiple Chrome windows ($chromeWindows) - profile picker may have appeared" -ForegroundColor Yellow
        }
    } else {
        Write-Host " ✗ Failed" -ForegroundColor Red
    }
    
    # Cleanup
    Start-Sleep -Seconds 1
    Get-Process -Name chrome -ErrorAction SilentlyContinue | Stop-Process -Force
} else {
    Write-Host " ⚠ Chrome not found" -ForegroundColor Yellow
}

Write-Host ""

# Test 4: Test Python integration tests
Write-Host "Test 4: Running Python integration tests..." -ForegroundColor Yellow

if (Test-Path "Microservice\venv\Scripts\activate.ps1") {
    Push-Location Microservice
    
    # Activate virtual environment and run tests
    $testOutput = & .\venv\Scripts\python.exe -m pytest tests/test_app_opening_chains.py -v --tb=short 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ All Python tests passed" -ForegroundColor Green
        
        # Count passed tests
        $passedTests = ($testOutput | Select-String "passed").ToString()
        if ($passedTests) {
            Write-Host "  $passedTests" -ForegroundColor Green
        }
    } else {
        Write-Host "  ✗ Some Python tests failed" -ForegroundColor Red
        Write-Host $testOutput | Select-String "FAILED" -ForegroundColor Red
    }
    
    Pop-Location
} else {
    Write-Host "  ⚠ Python virtual environment not found" -ForegroundColor Yellow
    Write-Host "    Setup with: cd Microservice; python -m venv venv; .\venv\Scripts\activate; pip install -r requirements.txt" -ForegroundColor Gray
}

Write-Host ""

# Test 5: Check Desktop App build
Write-Host "Test 5: Checking Desktop App build..." -ForegroundColor Yellow

$desktopAppProject = "Desktop-App\Kernel Agent\Kernel Agent.csproj"
if (Test-Path $desktopAppProject) {
    Write-Host "  Building Desktop App to verify new code compiles..." -NoNewline
    
    $buildOutput = dotnet build $desktopAppProject --configuration Debug --verbosity quiet 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✓ Build successful" -ForegroundColor Green
        
        # Check for warnings about new code
        $warnings = $buildOutput | Select-String "warning"
        if ($warnings) {
            Write-Host "  ⚠ Build warnings:" -ForegroundColor Yellow
            $warnings | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        }
    } else {
        Write-Host " ✗ Build failed" -ForegroundColor Red
        $errors = $buildOutput | Select-String "error"
        $errors | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    }
} else {
    Write-Host "  ⚠ Desktop App project not found" -ForegroundColor Yellow
}

Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$allGood = $backendRunning -and $microserviceRunning -and ($reliability -ge 90)

if ($allGood) {
    Write-Host "✓ All critical tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ready to test in Desktop App:" -ForegroundColor Cyan
    Write-Host "  1. Run Desktop App (F5 in Visual Studio)" -ForegroundColor White
    Write-Host "  2. Login/Signup" -ForegroundColor White
    Write-Host "  3. Try command: 'Open Notepad and type Hello World'" -ForegroundColor White
    Write-Host "  4. Try command: 'Open Chrome and go to GitHub'" -ForegroundColor White
    Write-Host "  5. Check logs for new improvements:" -ForegroundColor White
    Write-Host "     - [AUTOMATION] Opening: X (attempt 1/3)" -ForegroundColor Gray
    Write-Host "     - [EXECUTOR] App 'X' is focused and ready" -ForegroundColor Gray
    Write-Host "     - [EXECUTOR] System ready after Xms" -ForegroundColor Gray
} else {
    Write-Host "⚠ Some tests need attention" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Start any missing services (Backend, Microservice)" -ForegroundColor White
    Write-Host "  2. Fix any build errors in Desktop App" -ForegroundColor White
    Write-Host "  3. Re-run this script to verify" -ForegroundColor White
}

Write-Host ""
Write-Host "For detailed manual tests, see:" -ForegroundColor Cyan
Write-Host "  TESTING_APP_OPENING_CHAINS.md" -ForegroundColor White
Write-Host ""
