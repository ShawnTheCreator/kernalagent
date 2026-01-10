# Quick Backend Test Script
# Tests if backend is running and accessible

Write-Host "=== Testing Backend Connection ===" -ForegroundColor Cyan
Write-Host ""

$backendUrl = "http://localhost:5042"
$healthUrl = "$backendUrl/api/auth/me"

try {
    Write-Host "Testing backend at $backendUrl..." -ForegroundColor Yellow
    
    # Try to connect to backend
    $response = Invoke-WebRequest -Uri "$backendUrl/swagger" -Method Get -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✅ Backend is running!" -ForegroundColor Green
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor White
    Write-Host ""
    Write-Host "Swagger UI: https://localhost:7062/swagger" -ForegroundColor Cyan
    Write-Host "API Base: $backendUrl/api" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Backend is not running or not accessible" -ForegroundColor Red
    Write-Host ""
    Write-Host "To start the backend:" -ForegroundColor Yellow
    Write-Host "1. cd Backend\KernalAgentBackend" -ForegroundColor White
    Write-Host "2. dotnet run" -ForegroundColor White
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

