#!/usr/bin/env pwsh
# Test script for new advanced actions
# Just run: .\test-advanced-actions.ps1

$apiUrl = "http://localhost:5042/api"
$tempDir = "$env:TEMP\kernel_test"

# Create test directory
if (-not (Test-Path $tempDir)) {
    mkdir $tempDir | Out-Null
}

Write-Host "🧪 Testing Kernel Advanced Actions" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

function Test-Action {
    param($name, $body)
    try {
        $result = Invoke-RestMethod "$apiUrl/executor" -Method Post `
            -Body ($body | ConvertTo-Json) `
            -ContentType "application/json" `
            -ErrorAction Stop
        
        if ($result.success) {
            Write-Host "✓ $name" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ $name - $($result.error)" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "✗ $name - Connection error" -ForegroundColor Red
        return $false
    }
}

$passed = 0
$total = 0

# Test 1: Create file
$total++
if (Test-Action "Create file" @{
    action = "create_file"
    path = "$tempDir\test.txt"
    content = "Hello from Kernel Agent"
}) {
    $passed++
}

# Test 2: List files
$total++
if (Test-Action "List files" @{
    action = "list_files"
    path = $tempDir
}) {
    $passed++
}

# Test 3: Copy file
$total++
if (Test-Action "Copy file" @{
    action = "copy_file"
    source = "$tempDir\test.txt"
    destination = "$tempDir\test_copy.txt"
}) {
    $passed++
}

# Test 4: Rename file
$total++
if (Test-Action "Rename file" @{
    action = "rename_file"
    path = "$tempDir\test_copy.txt"
    new_name = "renamed.txt"
}) {
    $passed++
}

# Test 5: Get process list
$total++
if (Test-Action "Get process list" @{
    action = "get_process_list"
}) {
    $passed++
}

# Test 6: Check if process running
$total++
if (Test-Action "Check process running" @{
    action = "is_process_running"
    process_name = "explorer"
}) {
    $passed++
}

# Test 7: Copy to clipboard
$total++
if (Test-Action "Copy to clipboard" @{
    action = "copy_to_clipboard"
    content = "Copied from Kernel!"
}) {
    $passed++
}

# Test 8: Find files
$total++
if (Test-Action "Find files" @{
    action = "find_files"
    path = $tempDir
    pattern = "*.txt"
}) {
    $passed++
}

# Test 9: Delete files
$total++
if (Test-Action "Delete file" @{
    action = "delete_file"
    path = "$tempDir\test.txt"
}) {
    $passed++
}

# Cleanup
Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Results: $passed/$total tests passed" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Yellow" })

if ($passed -eq $total) {
    Write-Host "✅ All tests passed! Your kernel is enhanced!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some tests failed. Check if backend is running: 'dotnet run' in Backend folder" -ForegroundColor Yellow
}
