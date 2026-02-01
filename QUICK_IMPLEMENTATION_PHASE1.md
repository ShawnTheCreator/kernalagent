# Quick Implementation Guide - Advanced Actions

## Phase 1: Add File Operations to SmartExecutor.cs

Copy and paste this code into the **switch statement** in `ExecuteSingleAction()` method around **line 1670+**

```csharp
// ===== FILE OPERATIONS =====
case "create_file":
    if (step.TryGetProperty("path", out var pathEl) && 
        step.TryGetProperty("content", out var contentEl))
    {
        string filePath = pathEl.GetString() ?? "";
        string content = contentEl.GetString() ?? "";
        try
        {
            var directory = Path.GetDirectoryName(filePath);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }
            File.WriteAllText(filePath, content);
            result.Success = true;
            Debug.WriteLine($"[EXECUTOR] ✓ Created file: {filePath}");
        }
        catch (Exception ex)
        {
            result.Error = $"File creation failed: {ex.Message}";
            Debug.WriteLine($"[EXECUTOR] ✗ {result.Error}");
        }
    }
    break;

case "delete_file":
    if (step.TryGetProperty("path", out var delPathEl))
    {
        string filePath = delPathEl.GetString() ?? "";
        try
        {
            if (File.Exists(filePath))
            {
                File.Delete(filePath);
                result.Success = true;
                Debug.WriteLine($"[EXECUTOR] ✓ Deleted file: {filePath}");
            }
            else if (Directory.Exists(filePath))
            {
                Directory.Delete(filePath, true);
                result.Success = true;
                Debug.WriteLine($"[EXECUTOR] ✓ Deleted directory: {filePath}");
            }
            else
            {
                result.Error = $"Path not found: {filePath}";
            }
        }
        catch (Exception ex)
        {
            result.Error = $"Deletion failed: {ex.Message}";
        }
    }
    break;

case "copy_file":
    if (step.TryGetProperty("source", out var srcEl) && 
        step.TryGetProperty("destination", out var destEl))
    {
        string source = srcEl.GetString() ?? "";
        string destination = destEl.GetString() ?? "";
        try
        {
            var destDir = Path.GetDirectoryName(destination);
            if (!string.IsNullOrEmpty(destDir) && !Directory.Exists(destDir))
            {
                Directory.CreateDirectory(destDir);
            }
            File.Copy(source, destination, overwrite: true);
            result.Success = true;
            Debug.WriteLine($"[EXECUTOR] ✓ Copied {source} to {destination}");
        }
        catch (Exception ex)
        {
            result.Error = $"Copy failed: {ex.Message}";
        }
    }
    break;

case "move_file":
    if (step.TryGetProperty("source", out var moveSrcEl) && 
        step.TryGetProperty("destination", out var moveDestEl))
    {
        string source = moveSrcEl.GetString() ?? "";
        string destination = moveDestEl.GetString() ?? "";
        try
        {
            var destDir = Path.GetDirectoryName(destination);
            if (!string.IsNullOrEmpty(destDir) && !Directory.Exists(destDir))
            {
                Directory.CreateDirectory(destDir);
            }
            if (File.Exists(destination))
                File.Delete(destination);
            File.Move(source, destination);
            result.Success = true;
            Debug.WriteLine($"[EXECUTOR] ✓ Moved {source} to {destination}");
        }
        catch (Exception ex)
        {
            result.Error = $"Move failed: {ex.Message}";
        }
    }
    break;

case "list_files":
    if (step.TryGetProperty("path", out var listPathEl))
    {
        string dirPath = listPathEl.GetString() ?? "";
        try
        {
            if (!Directory.Exists(dirPath))
            {
                result.Error = $"Directory not found: {dirPath}";
            }
            else
            {
                var files = Directory.GetFiles(dirPath);
                var folders = Directory.GetDirectories(dirPath);
                var all = files.Concat(folders).ToList();
                result.Success = true;
                result.Details = string.Join("|", all.Select(p => Path.GetFileName(p)));
                Debug.WriteLine($"[EXECUTOR] ✓ Listed {all.Count} items in {dirPath}");
            }
        }
        catch (Exception ex)
        {
            result.Error = $"List failed: {ex.Message}";
        }
    }
    break;

case "get_file_info":
    if (step.TryGetProperty("path", out var infoPathEl))
    {
        string filePath = infoPathEl.GetString() ?? "";
        try
        {
            if (File.Exists(filePath))
            {
                var info = new FileInfo(filePath);
                result.Success = true;
                result.Details = $"Size:{info.Length}|Modified:{info.LastWriteTime}|Name:{info.Name}";
            }
            else if (Directory.Exists(filePath))
            {
                var info = new DirectoryInfo(filePath);
                result.Success = true;
                result.Details = $"Files:{Directory.GetFiles(filePath).Length}|Folders:{Directory.GetDirectories(filePath).Length}|Created:{info.CreationTime}";
            }
            else
            {
                result.Error = $"Path not found: {filePath}";
            }
        }
        catch (Exception ex)
        {
            result.Error = $"Get info failed: {ex.Message}";
        }
    }
    break;

case "rename_file":
    if (step.TryGetProperty("path", out var renameSrcEl) && 
        step.TryGetProperty("new_name", out var renameDestEl))
    {
        string filePath = renameSrcEl.GetString() ?? "";
        string newName = renameDestEl.GetString() ?? "";
        try
        {
            var directory = Path.GetDirectoryName(filePath);
            var newPath = Path.Combine(directory, newName);
            if (File.Exists(filePath))
            {
                File.Move(filePath, newPath, overwrite: true);
                result.Success = true;
            }
            else if (Directory.Exists(filePath))
            {
                Directory.Move(filePath, newPath);
                result.Success = true;
            }
        }
        catch (Exception ex)
        {
            result.Error = $"Rename failed: {ex.Message}";
        }
    }
    break;

// ===== CLIPBOARD OPERATIONS =====
case "copy_to_clipboard":
    if (step.TryGetProperty("content", out var clipEl))
    {
        string content = clipEl.GetString() ?? "";
        try
        {
            var thread = new Thread(() => 
            {
                System.Windows.Forms.Clipboard.SetText(content);
            });
            thread.SetApartmentState(ApartmentState.STA);
            thread.Start();
            thread.Join(1000);
            result.Success = true;
            Debug.WriteLine("[EXECUTOR] ✓ Copied to clipboard");
        }
        catch (Exception ex)
        {
            result.Error = $"Clipboard copy failed: {ex.Message}";
        }
    }
    break;

case "paste_from_clipboard":
    try
    {
        string clipboard = "";
        var thread = new Thread(() => 
        {
            try
            {
                clipboard = System.Windows.Forms.Clipboard.GetText();
            }
            catch { }
        });
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        thread.Join(1000);
        
        if (!string.IsNullOrEmpty(clipboard))
        {
            _automation.TypeIntoApp(clipboard);
            result.Success = true;
            Debug.WriteLine("[EXECUTOR] ✓ Pasted from clipboard");
        }
        else
        {
            result.Error = "Clipboard is empty";
        }
    }
    catch (Exception ex)
    {
        result.Error = $"Clipboard paste failed: {ex.Message}";
    }
    break;

// ===== PROCESS CONTROL =====
case "get_process_list":
    try
    {
        var processes = System.Diagnostics.Process.GetProcesses()
            .Select(p => p.ProcessName)
            .Distinct()
            .OrderBy(p => p)
            .ToList();
        result.Success = true;
        result.Details = string.Join("|", processes);
        Debug.WriteLine($"[EXECUTOR] ✓ Listed {processes.Count} processes");
    }
    catch (Exception ex)
    {
        result.Error = $"Process list failed: {ex.Message}";
    }
    break;

case "kill_process":
    if (step.TryGetProperty("process_name", out var procEl))
    {
        string processName = procEl.GetString()?.Replace(".exe", "").Replace(".EXE", "") ?? "";
        try
        {
            var processes = System.Diagnostics.Process.GetProcessesByName(processName);
            foreach (var proc in processes)
            {
                proc.Kill();
                proc.WaitForExit(3000);
            }
            result.Success = processes.Length > 0;
            if (result.Success)
                Debug.WriteLine($"[EXECUTOR] ✓ Killed {processes.Length} process(es): {processName}");
            else
                result.Error = $"Process not found: {processName}";
        }
        catch (Exception ex)
        {
            result.Error = $"Kill process failed: {ex.Message}";
        }
    }
    break;

case "is_process_running":
    if (step.TryGetProperty("process_name", out var checkProcEl))
    {
        string processName = checkProcEl.GetString()?.Replace(".exe", "") ?? "";
        try
        {
            var processes = System.Diagnostics.Process.GetProcessesByName(processName);
            result.Success = processes.Length > 0;
            result.Details = processes.Length.ToString();
            Debug.WriteLine($"[EXECUTOR] ✓ Found {processes.Length} instance(s) of {processName}");
        }
        catch (Exception ex)
        {
            result.Error = $"Process check failed: {ex.Message}";
        }
    }
    break;

// ===== WINDOW OPERATIONS =====
case "get_active_window":
    try
    {
        IntPtr handle = GetForegroundWindow();
        string windowTitle = GetWindowTitle(handle);
        result.Success = !string.IsNullOrEmpty(windowTitle);
        result.Details = windowTitle;
        Debug.WriteLine($"[EXECUTOR] ✓ Active window: {windowTitle}");
    }
    catch (Exception ex)
    {
        result.Error = $"Get active window failed: {ex.Message}";
    }
    break;

case "find_window":
    if (step.TryGetProperty("title", out var findTitleEl))
    {
        string windowTitle = findTitleEl.GetString() ?? "";
        try
        {
            var handle = FindWindowByTitle(windowTitle);
            result.Success = handle != IntPtr.Zero;
            if (result.Success)
                result.Details = handle.ToString();
            else
                result.Error = $"Window not found: {windowTitle}";
        }
        catch (Exception ex)
        {
            result.Error = $"Find window failed: {ex.Message}";
        }
    }
    break;

case "get_window_list":
    try
    {
        var windows = GetAllVisibleWindows();
        result.Success = true;
        result.Details = string.Join("|", windows);
        Debug.WriteLine($"[EXECUTOR] ✓ Found {windows.Count} open windows");
    }
    catch (Exception ex)
    {
        result.Error = $"Get window list failed: {ex.Message}";
    }
    break;

// ===== SMART WAITING =====
case "wait_for_window":
    if (step.TryGetProperty("title", out var waitTitleEl))
    {
        string windowTitle = waitTitleEl.GetString() ?? "";
        int timeout = step.TryGetProperty("timeout_ms", out var timeoutEl) 
            ? timeoutEl.GetInt32() : 10000;
        
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        bool found = false;
        
        while (stopwatch.ElapsedMilliseconds < timeout && !found)
        {
            var handle = FindWindowByTitle(windowTitle);
            if (handle != IntPtr.Zero)
            {
                found = true;
                result.Success = true;
                break;
            }
            await Task.Delay(100);
        }
        
        if (!result.Success)
            result.Error = $"Window '{windowTitle}' not found within {timeout}ms";
        else
            Debug.WriteLine($"[EXECUTOR] ✓ Window found: {windowTitle}");
    }
    break;

case "wait_for_file_exists":
    if (step.TryGetProperty("path", out var waitFileEl))
    {
        string filePath = waitFileEl.GetString() ?? "";
        int timeout = step.TryGetProperty("timeout_ms", out var fileTimeoutEl) 
            ? fileTimeoutEl.GetInt32() : 10000;
        
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        
        while (stopwatch.ElapsedMilliseconds < timeout)
        {
            if (File.Exists(filePath) || Directory.Exists(filePath))
            {
                result.Success = true;
                Debug.WriteLine($"[EXECUTOR] ✓ File/folder exists: {filePath}");
                break;
            }
            await Task.Delay(200);
        }
        
        if (!result.Success)
            result.Error = $"File/folder '{filePath}' not found within {timeout}ms";
    }
    break;

// ===== SEARCH & EXTRACT =====
case "find_files":
    if (step.TryGetProperty("path", out var searchPathEl) && 
        step.TryGetProperty("pattern", out var patternEl))
    {
        string directory = searchPathEl.GetString() ?? "";
        string pattern = patternEl.GetString() ?? "*";
        try
        {
            var files = Directory.GetFiles(directory, pattern, SearchOption.TopDirectoryOnly);
            result.Success = true;
            result.Details = string.Join("|", files.Select(f => Path.GetFileName(f)));
            Debug.WriteLine($"[EXECUTOR] ✓ Found {files.Length} files matching '{pattern}'");
        }
        catch (Exception ex)
        {
            result.Error = $"Find files failed: {ex.Message}";
        }
    }
    break;

case "search_files_recursive":
    if (step.TryGetProperty("path", out var recSearchPathEl) && 
        step.TryGetProperty("pattern", out var recPatternEl))
    {
        string directory = recSearchPathEl.GetString() ?? "";
        string pattern = recPatternEl.GetString() ?? "*";
        try
        {
            var files = Directory.GetFiles(directory, pattern, SearchOption.AllDirectories)
                .Take(100) // Limit to prevent overflow
                .ToArray();
            result.Success = true;
            result.Details = string.Join("|", files.Select(f => Path.GetFileName(f)));
            Debug.WriteLine($"[EXECUTOR] ✓ Found {files.Length} files (recursive)");
        }
        catch (Exception ex)
        {
            result.Error = $"Recursive search failed: {ex.Message}";
        }
    }
    break;
```

---

## Phase 2: Add Helper Methods to SmartExecutor.cs

Add these helper methods to the **SmartExecutor class** (after the ExecuteSingleAction method):

```csharp
// ===== WINDOW HELPERS =====
[System.Runtime.InteropServices.DllImport("user32.dll")]
private static extern IntPtr GetForegroundWindow();

[System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
private static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);

[System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
private static extern int GetWindowTextLength(IntPtr hWnd);

[System.Runtime.InteropServices.DllImport("user32.dll")]
private static extern bool IsWindowVisible(IntPtr hWnd);

[System.Runtime.InteropServices.DllImport("user32.dll")]
private static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);

private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

private static string GetWindowTitle(IntPtr hWnd)
{
    int length = GetWindowTextLength(hWnd);
    if (length == 0) return "";
    
    var sb = new System.Text.StringBuilder(length + 1);
    GetWindowText(hWnd, sb, sb.Capacity);
    return sb.ToString();
}

private static IntPtr FindWindowByTitle(string titlePartial)
{
    IntPtr result = IntPtr.Zero;
    
    EnumWindows((hWnd, lParam) =>
    {
        if (IsWindowVisible(hWnd))
        {
            string title = GetWindowTitle(hWnd);
            if (title.IndexOf(titlePartial, StringComparison.OrdinalIgnoreCase) >= 0)
            {
                result = hWnd;
                return false; // Stop enum
            }
        }
        return true; // Continue enum
    }, IntPtr.Zero);
    
    return result;
}

private static List<string> GetAllVisibleWindows()
{
    var windows = new List<string>();
    
    EnumWindows((hWnd, lParam) =>
    {
        if (IsWindowVisible(hWnd))
        {
            string title = GetWindowTitle(hWnd);
            if (!string.IsNullOrEmpty(title) && title.Length < 100)
            {
                windows.Add(title);
            }
        }
        return true; // Continue enum
    }, IntPtr.Zero);
    
    return windows;
}
```

---

## Phase 3: Test Your New Actions

Create a test script: `test-new-actions.ps1`

```powershell
# Test file operations
$testFile = "$env:TEMP\kernel_test.txt"
$testContent = "Hello from Kernel Agent $(Get-Date)"

# Create file
$createResult = Invoke-RestMethod -Uri "http://localhost:5042/api/executor" -Method Post -Body @{
    action = "create_file"
    path = $testFile
    content = $testContent
} -ContentType "application/json"

Write-Host "✓ Create file:" $createResult.success

# List files in temp
$listResult = Invoke-RestMethod -Uri "http://localhost:5042/api/executor" -Method Post -Body @{
    action = "list_files"
    path = "$env:TEMP"
} -ContentType "application/json"

Write-Host "✓ List files:" $listResult.details.Split('|').Count "files found"

# Copy file
$copyResult = Invoke-RestMethod -Uri "http://localhost:5042/api/executor" -Method Post -Body @{
    action = "copy_file"
    source = $testFile
    destination = "$env:TEMP\kernel_test_copy.txt"
} -ContentType "application/json"

Write-Host "✓ Copy file:" $copyResult.success

# Get process list
$procResult = Invoke-RestMethod -Uri "http://localhost:5042/api/executor" -Method Post -Body @{
    action = "get_process_list"
} -ContentType "application/json"

$procCount = $procResult.details.Split('|').Count
Write-Host "✓ Get processes: Found $procCount processes"

# Check if process running
$checkResult = Invoke-RestMethod -Uri "http://localhost:5042/api/executor" -Method Post -Body @{
    action = "is_process_running"
    process_name = "explorer"
} -ContentType "application/json"

Write-Host "✓ Check process: explorer.exe running =" $checkResult.success

# Get active window
$activeResult = Invoke-RestMethod -Uri "http://localhost:5042/api/executor" -Method Post -Body @{
    action = "get_active_window"
} -ContentType "application/json"

Write-Host "✓ Active window:" $activeResult.details

# Cleanup
Remove-Item $testFile -ErrorAction SilentlyContinue
Remove-Item "$env:TEMP\kernel_test_copy.txt" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "All tests completed!" -ForegroundColor Green
```

Run with:
```powershell
cd c:\Users\anime\3D Objects\Ghost
.\test-new-actions.ps1
```

---

## Advanced Example: File Organization Automation

JSON action plan for organizing downloads:

```json
{
  "goal": "Organize Downloads folder",
  "actions": [
    {
      "action": "open_app",
      "target": "explorer.exe"
    },
    {
      "action": "wait_for_window",
      "title": "File Explorer",
      "timeout_ms": 5000
    },
    {
      "action": "navigate",
      "url": "shell:Downloads"
    },
    {
      "action": "wait_for_file_exists",
      "path": "Documents",
      "timeout_ms": 2000
    },
    {
      "action": "list_files",
      "path": "."
    },
    {
      "action": "find_files",
      "path": ".",
      "pattern": "*.pdf"
    },
    {
      "action": "move_file",
      "source": "*.pdf",
      "destination": "Documents\\PDFs"
    }
  ]
}
```

---

## Integration Notes

1. **Add `using System.Threading;` at top** of SmartExecutor.cs
2. **No database changes needed** - These use file system only
3. **Add logging** - All operations are already logged with Debug.WriteLine
4. **Security** - Consider adding path validation via SecurityPolicyService

---

## Next: Add to Microservice for Remote Planning

Once file operations work in Desktop app, add task planning in Microservice:

Create `Microservice/app/agents/autonomous_task.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class TaskGoal(BaseModel):
    goal: str
    max_steps: int = 20

@router.post("/autonomous/plan")
async def plan_autonomous_task(task: TaskGoal):
    """
    AI generates step-by-step plan for complex tasks
    
    Example:
    Goal: "Organize my downloads folder and delete duplicates"
    Output: [Step 1: Open Explorer, Step 2: Navigate to Downloads, ...]
    """
    # TODO: Call Gemini with task goal
    # Return structured steps that SmartExecutor can execute
    pass
```

This will create an **end-to-end autonomous system**! 🚀
