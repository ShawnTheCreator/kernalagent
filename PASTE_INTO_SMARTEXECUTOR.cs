// PASTE THIS INTO SmartExecutor.cs in ExecuteSingleAction() switch statement
// Around line 1670, after the last existing case, before the closing braces

case "create_file":
    if (step.TryGetProperty("path", out var pathEl) && 
        step.TryGetProperty("content", out var contentEl))
    {
        string filePath = pathEl.GetString() ?? "";
        string content = contentEl.GetString() ?? "";
        result.Success = AdvancedActions.CreateFile(filePath, content);
    }
    break;

case "delete_file":
    if (step.TryGetProperty("path", out var delPathEl))
    {
        string filePath = delPathEl.GetString() ?? "";
        result.Success = AdvancedActions.DeleteFile(filePath);
    }
    break;

case "copy_file":
    if (step.TryGetProperty("source", out var srcEl) && 
        step.TryGetProperty("destination", out var destEl))
    {
        string source = srcEl.GetString() ?? "";
        string destination = destEl.GetString() ?? "";
        result.Success = AdvancedActions.CopyFile(source, destination);
    }
    break;

case "move_file":
    if (step.TryGetProperty("source", out var moveSrcEl) && 
        step.TryGetProperty("destination", out var moveDestEl))
    {
        string source = moveSrcEl.GetString() ?? "";
        string destination = moveDestEl.GetString() ?? "";
        result.Success = AdvancedActions.MoveFile(source, destination);
    }
    break;

case "list_files":
    if (step.TryGetProperty("path", out var listPathEl))
    {
        string dirPath = listPathEl.GetString() ?? "";
        result.Details = AdvancedActions.ListFiles(dirPath);
        result.Success = !string.IsNullOrEmpty(result.Details);
    }
    break;

case "find_files":
    if (step.TryGetProperty("path", out var searchPathEl) && 
        step.TryGetProperty("pattern", out var patternEl))
    {
        string directory = searchPathEl.GetString() ?? "";
        string pattern = patternEl.GetString() ?? "*";
        result.Details = AdvancedActions.FindFiles(directory, pattern);
        result.Success = !string.IsNullOrEmpty(result.Details);
    }
    break;

case "rename_file":
    if (step.TryGetProperty("path", out var renameSrcEl) && 
        step.TryGetProperty("new_name", out var renameDestEl))
    {
        string filePath = renameSrcEl.GetString() ?? "";
        string newName = renameDestEl.GetString() ?? "";
        result.Success = AdvancedActions.RenameFile(filePath, newName);
    }
    break;

case "get_process_list":
    var processes = AdvancedActions.GetProcessList();
    result.Success = true;
    result.Details = string.Join("|", processes);
    break;

case "kill_process":
    if (step.TryGetProperty("process_name", out var procEl))
    {
        string processName = procEl.GetString() ?? "";
        result.Success = AdvancedActions.KillProcess(processName);
    }
    break;

case "is_process_running":
    if (step.TryGetProperty("process_name", out var checkProcEl))
    {
        string processName = checkProcEl.GetString() ?? "";
        result.Success = AdvancedActions.IsProcessRunning(processName);
    }
    break;

case "copy_to_clipboard":
    if (step.TryGetProperty("content", out var clipEl))
    {
        string content = clipEl.GetString() ?? "";
        result.Success = AdvancedActions.CopyToClipboard(content);
    }
    break;

case "paste_from_clipboard":
    string clipboard = AdvancedActions.PasteFromClipboard();
    if (!string.IsNullOrEmpty(clipboard))
    {
        _automation.TypeIntoApp(clipboard);
        result.Success = true;
    }
    break;
