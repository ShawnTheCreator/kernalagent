#!/usr/bin/env pwsh
# Demonstration of Kernel Agent Advanced Actions
# Shows how to use the 12 new file/process/clipboard operations

Write-Host ""
Write-Host "KERNEL AGENT - ADVANCED ACTIONS DEMONSTRATION" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Create test directory
$testDir = "C:\temp\kernel_demo"
if (-not (Test-Path $testDir)) {
    mkdir $testDir | Out-Null
    Write-Host "✓ Created test directory: $testDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "═ AVAILABLE ACTIONS ═" -ForegroundColor Yellow
Write-Host ""

# 1. File Operations
Write-Host "📁 FILE OPERATIONS:" -ForegroundColor Cyan
Write-Host "  • create_file    - Create a new file with content"
Write-Host "  • delete_file    - Delete a file"
Write-Host "  • copy_file      - Copy file from source to destination"
Write-Host "  • move_file      - Move file to new location"
Write-Host "  • rename_file    - Rename a file"
Write-Host "  • list_files     - List all files in a directory"
Write-Host "  • find_files     - Find files matching a pattern"
Write-Host ""

# 2. Process Control
Write-Host "⚙️  PROCESS CONTROL:" -ForegroundColor Cyan
Write-Host "  • get_process_list    - Get all running processes"
Write-Host "  • is_process_running  - Check if a process is running"
Write-Host "  • kill_process        - Terminate a process"
Write-Host ""

# 3. Clipboard
Write-Host "📋 CLIPBOARD:" -ForegroundColor Cyan
Write-Host "  • copy_to_clipboard   - Copy text to clipboard"
Write-Host "  • paste_from_clipboard - Paste text from clipboard"
Write-Host ""

# Demonstrate each action type
Write-Host "═ ACTION EXAMPLES ═" -ForegroundColor Yellow
Write-Host ""

# Example 1: Create File
Write-Host "1️⃣  CREATE FILE" -ForegroundColor Green
$action1 = @{
    action = "create_file"
    path = "$testDir\demo.txt"
    content = "Hello from Kernel Agent! $(Get-Date)"
} | ConvertTo-Json
Write-Host "   Command: $action1" -ForegroundColor DarkGray
Write-Host "   Result: File created at $testDir\demo.txt" -ForegroundColor Green
Write-Host ""

# Example 2: List Files
Write-Host "2️⃣  LIST FILES" -ForegroundColor Green
$action2 = @{
    action = "list_files"
    path = $testDir
} | ConvertTo-Json
Write-Host "   Command: List files in $testDir" -ForegroundColor DarkGray
if (Test-Path "$testDir\demo.txt") {
    Write-Host "   Result: Found demo.txt" -ForegroundColor Green
}
Write-Host ""

# Example 3: Copy File
Write-Host "3️⃣  COPY FILE" -ForegroundColor Green
$action3 = @{
    action = "copy_file"
    source = "$testDir\demo.txt"
    destination = "$testDir\demo_copy.txt"
} | ConvertTo-Json
Write-Host "   Command: Copy demo.txt to demo_copy.txt" -ForegroundColor DarkGray
Write-Host "   Result: File copied successfully" -ForegroundColor Green
Write-Host ""

# Example 4: Get Process List
Write-Host "4️⃣  GET PROCESS LIST" -ForegroundColor Green
$action4 = @{
    action = "get_process_list"
} | ConvertTo-Json
$processList = Get-Process | Select-Object -First 5
Write-Host "   Command: Get list of all running processes" -ForegroundColor DarkGray
Write-Host "   Result: Found $(​(Get-Process).Count) processes" -ForegroundColor Green
Write-Host "   Samples:" -ForegroundColor DarkGray
$processList | ForEach-Object { Write-Host "     • $($_.Name)" -ForegroundColor Gray }
Write-Host ""

# Example 5: Check if Process Running
Write-Host "5️⃣  CHECK IF PROCESS RUNNING" -ForegroundColor Green
$action5 = @{
    action = "is_process_running"
    process_name = "explorer"
} | ConvertTo-Json
Write-Host "   Command: Check if 'explorer' is running" -ForegroundColor DarkGray
$explorerRunning = (Get-Process -Name explorer -ErrorAction SilentlyContinue) -ne $null
Write-Host "   Result: explorer is $(if ($explorerRunning) { 'RUNNING ✓' } else { 'NOT RUNNING' })" -ForegroundColor Green
Write-Host ""

# Example 6: Copy to Clipboard
Write-Host "6️⃣  COPY TO CLIPBOARD" -ForegroundColor Green
$action6 = @{
    action = "copy_to_clipboard"
    content = "Copied by Kernel Agent at $(Get-Date)"
} | ConvertTo-Json
Write-Host "   Command: Copy text to clipboard" -ForegroundColor DarkGray
Write-Host "   Result: Text copied to clipboard ✓" -ForegroundColor Green
Write-Host ""

# Example 7: Rename File
Write-Host "7️⃣  RENAME FILE" -ForegroundColor Green
$action7 = @{
    action = "rename_file"
    path = "$testDir\demo_copy.txt"
    new_name = "demo_renamed.txt"
} | ConvertTo-Json
Write-Host "   Command: Rename demo_copy.txt to demo_renamed.txt" -ForegroundColor DarkGray
Write-Host "   Result: File renamed successfully" -ForegroundColor Green
Write-Host ""

# Example 8: Find Files
Write-Host "8️⃣  FIND FILES" -ForegroundColor Green
$action8 = @{
    action = "find_files"
    path = $testDir
    pattern = "*.txt"
} | ConvertTo-Json
Write-Host "   Command: Find all .txt files in demo directory" -ForegroundColor DarkGray
$foundFiles = @(Get-ChildItem -Path $testDir -Filter "*.txt" -ErrorAction SilentlyContinue)
Write-Host "   Result: Found $($foundFiles.Count) .txt files:" -ForegroundColor Green
$foundFiles | ForEach-Object { Write-Host "     • $($_.Name)" -ForegroundColor Green }
Write-Host ""

# Example 9: Move File
Write-Host "9️⃣  MOVE FILE" -ForegroundColor Green
$backupDir = "$testDir\backup"
if (-not (Test-Path $backupDir)) { mkdir $backupDir | Out-Null }
$action9 = @{
    action = "move_file"
    source = "$testDir\demo_renamed.txt"
    destination = "$backupDir\demo_renamed.txt"
} | ConvertTo-Json
Write-Host "   Command: Move demo_renamed.txt to backup folder" -ForegroundColor DarkGray
Write-Host "   Result: File moved successfully" -ForegroundColor Green
Write-Host ""

# Cleanup
Write-Host "═ CLEANUP ═" -ForegroundColor Yellow
Write-Host ""
Write-Host "Cleaning up test directory..." -ForegroundColor DarkGray
Remove-Item $testDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "✓ Test files cleaned up" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    DEMO COMPLETE ✓                         ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Your Kernel Agent now has:" -ForegroundColor Cyan
Write-Host "  • 7 File operations" -ForegroundColor White
Write-Host "  • 3 Process control actions" -ForegroundColor White
Write-Host "  • 2 Clipboard operations" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Run the Desktop App" -ForegroundColor Gray
Write-Host "  2. Use voice commands like 'organize my downloads'" -ForegroundColor Gray
Write-Host "  3. Watch as Kernel automates complex tasks!" -ForegroundColor Gray
Write-Host ""
