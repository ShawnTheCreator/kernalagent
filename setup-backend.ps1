# Backend Setup Script
# This script helps you set up the backend .env file

Write-Host "=== Backend Environment Setup ===" -ForegroundColor Cyan
Write-Host ""

$backendPath = "Backend\KernalAgentBackend"
$envFile = Join-Path $backendPath ".env"
$envExample = Join-Path $backendPath ".env.example"

# Check if .env already exists
if (Test-Path $envFile) {
    Write-Host "⚠️  .env file already exists!" -ForegroundColor Yellow
    $overwrite = Read-Host "Do you want to overwrite it? (y/N)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "Skipping .env creation." -ForegroundColor Yellow
        exit
    }
}

# Generate a random JWT key
Write-Host "Generating secure JWT key..." -ForegroundColor Green
$jwtKey = -join ((48..57) + (65..90) + (97..122) + (33..47) | Get-Random -Count 64 | ForEach-Object {[char]$_})

# Create .env file
$envContent = @"
# JWT Configuration
JWT_KEY=$jwtKey
JWT_ISSUER=KernalAgentBackend
JWT_AUDIENCE=KernalAgentFrontend

# Database Configuration
# Leave empty to use InMemory database for development
DATABASE_CONNECTION_STRING=

# CORS Configuration (comma-separated)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
"@

$envContent | Out-File -FilePath $envFile -Encoding utf8

Write-Host "✅ .env file created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Location: $envFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Navigate to: $backendPath" -ForegroundColor White
Write-Host "2. Run: dotnet run" -ForegroundColor White
Write-Host "3. Open: https://localhost:7062/swagger" -ForegroundColor White
Write-Host ""

