using System;
using System.Threading.Tasks;
using System.Diagnostics;
using System.Text.Json;
using System.Net.Http;
using System.Text;
using System.Linq;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// SmartExecutor - Reliable action execution with verification, retry, and VISION RECOVERY.
    /// 
    /// Features:
    /// 1. Verification - checks if actions succeeded
    /// 2. Retry logic - retries failed actions with backoff
    /// 3. Smart timing - waits for apps to be ready
    /// 4. VISION RECOVERY - calls AI when stuck to auto-recover
    /// </summary>
    public class SmartExecutor
    {
        private readonly WindowsAutomation _automation;
        private readonly VisionRecoveryService _visionRecovery;
        private readonly UIElementFinder _uiFinder;  // NEW: UI Automation support
        private readonly ContextManager _context;    // NEW: Context tracking
        private const int MAX_RETRIES = 3;
        private const int BASE_DELAY_MS = 100;
        private string _currentGoal = "";  // Track original command for recovery
        private string _lastOpenedApp = ""; // Track last opened app for focus before typing
        
        // Actions that may trigger dialogs and need proactive checking
        private static readonly System.Collections.Generic.HashSet<string> RiskyActions = new() {
            "save", "hotkey", "press_key", "type_text"
        };
        
        // Hotkeys that commonly trigger dialogs
        private static readonly System.Collections.Generic.HashSet<string> DialogTriggerHotkeys = new() {
            "ctrl+s", "ctrl+shift+s", "ctrl+n", "ctrl+o", "ctrl+w", "alt+f4"
        };
        
        public SmartExecutor()
        {
            _automation = new WindowsAutomation();
            _visionRecovery = new VisionRecoveryService();
            _uiFinder = new UIElementFinder();  // NEW: Initialize UI finder
            _context = ContextManager.Instance;  // NEW: Get context singleton
        }
        
        public void SetOriginalGoal(string goal)
        {
            _currentGoal = goal;
        }
        
        /// <summary>
        /// Get current context for sending to Python backend.
        /// </summary>
        public System.Collections.Generic.Dictionary<string, object> GetContext()
        {
            _context.RefreshContext();
            return _context.GetContextDict();
        }

        /// <summary>
        /// Execute a single action with verification and retry.
        /// </summary>
        public async Task<ExecutionResult> ExecuteActionAsync(JsonElement step)
        {
            string action = "";
            if (step.TryGetProperty("action", out JsonElement actionEl))
            {
                action = actionEl.GetString() ?? "";
            }

            if (string.IsNullOrEmpty(action))
            {
                return new ExecutionResult { Success = false, Action = action, Error = "Empty action" };
            }

            Debug.WriteLine($"[EXECUTOR] Starting: {action}");
            var stopwatch = Stopwatch.StartNew();

            for (int attempt = 1; attempt <= MAX_RETRIES; attempt++)
            {
                try
                {
                    var result = await ExecuteSingleAction(action, step);
                    
                    if (result.Success)
                    {
                        stopwatch.Stop();
                        result.ExecutionTimeMs = (int)stopwatch.ElapsedMilliseconds;
                        Debug.WriteLine($"[EXECUTOR] ✓ {action} completed in {result.ExecutionTimeMs}ms");
                        
                        // Report to frontend via WebSocket
                        string target = "";
                        if (step.TryGetProperty("target", out var targetEl))
                            target = targetEl.GetString() ?? "";
                        if (step.TryGetProperty("content", out var contentEl))
                            target = contentEl.GetString() ?? target;
                        _ = Task.Run(async () => 
                        {
                            await BrainConnectionService.Instance.ReportActionAsync(action, target, $"Completed in {result.ExecutionTimeMs}ms");
                        });
                        
                        return result;
                    }
                    
                    // If failed and has retries left, wait and retry
                    if (attempt < MAX_RETRIES)
                    {
                        int delay = BASE_DELAY_MS * (int)Math.Pow(2, attempt - 1); // Exponential backoff
                        Debug.WriteLine($"[EXECUTOR] ⚠ {action} failed (attempt {attempt}), retrying in {delay}ms...");
                        await Task.Delay(delay);
                    }
                }
                catch (Exception ex)
                {
                    Debug.WriteLine($"[EXECUTOR] ❌ {action} error: {ex.Message}");
                    
                    if (attempt == MAX_RETRIES)
                    {
                        return new ExecutionResult
                        {
                            Success = false,
                            Action = action,
                            Error = ex.Message,
                            ExecutionTimeMs = (int)stopwatch.ElapsedMilliseconds
                        };
                    }
                }
            }

            return new ExecutionResult { Success = false, Action = action, Error = "Max retries exceeded" };
        }

        /// <summary>
        /// Execute a plan (list of actions) with proper sequencing and VISION RECOVERY.
        /// Now includes PROACTIVE DIALOG DETECTION after risky actions.
        /// </summary>
        public async Task<PlanExecutionResult> ExecutePlanAsync(JsonElement stepsElement)
        {
            var result = new PlanExecutionResult();
            var stopwatch = Stopwatch.StartNew();
            int stepIndex = 0;
            int totalSteps = 0;
            
            // Count total steps
            foreach (var _ in stepsElement.EnumerateArray())
                totalSteps++;

            foreach (var step in stepsElement.EnumerateArray())
            {
                stepIndex++;
                var actionResult = await ExecuteActionAsync(step);
                result.ActionResults.Add(actionResult);
                
                // Get action details for dialog checking
                string actionName = "";
                string hotkeyContent = "";
                if (step.TryGetProperty("action", out var actionEl))
                    actionName = actionEl.GetString() ?? "";
                if (step.TryGetProperty("content", out var contentEl))
                    hotkeyContent = contentEl.GetString() ?? "";
                
                // ===== PROACTIVE DIALOG DETECTION =====
                // Check for dialogs after risky actions (save, hotkey, etc.)
                bool shouldCheckDialog = RiskyActions.Contains(actionName) ||
                    (actionName == "hotkey" && DialogTriggerHotkeys.Contains(hotkeyContent.ToLower()));
                
                if (shouldCheckDialog && actionResult.Success)
                {
                    Debug.WriteLine($"[EXECUTOR] Checking for dialog after: {actionName} ({hotkeyContent})");
                    
                    // Wait briefly for dialog to appear
                    await Task.Delay(500);
                    
                    var dialogInfo = await _automation.WaitForDialogAsync(1000);
                    
                    if (dialogInfo != null)
                    {
                        Debug.WriteLine($"[EXECUTOR] 🔔 DIALOG DETECTED: '{dialogInfo.Title}' (type={dialogInfo.Type})");
                        
                        // Handle known dialogs automatically
                        bool dialogHandled = await HandleKnownDialogAsync(dialogInfo);
                        
                        if (!dialogHandled)
                        {
                            // Unknown dialog - call vision recovery
                            Debug.WriteLine($"[EXECUTOR] Unknown dialog, calling vision recovery...");
                            
                            if (!string.IsNullOrEmpty(_currentGoal))
                            {
                                var recoveryResult = await _visionRecovery.AttemptRecoveryAsync(
                                    _currentGoal,
                                    actionName,
                                    $"Dialog appeared: {dialogInfo.Title}",
                                    dialogInfo.Title,
                                    "",
                                    null,
                                    stepIndex,
                                    totalSteps,
                                    actionName,
                                    true
                                );
                                
                                if (recoveryResult.Success && recoveryResult.RecoveryAction != null)
                                {
                                    Debug.WriteLine($"[EXECUTOR] Vision recovery suggests: {recoveryResult.RecoveryAction.Action}");
                                    var recoveryExec = await ExecuteRecoveryAction(recoveryResult.RecoveryAction);
                                    result.ActionResults.Add(recoveryExec);
                                }
                            }
                        }
                    }
                }
                // ===== END PROACTIVE DIALOG DETECTION =====

                if (!actionResult.Success)
                {
                    Debug.WriteLine($"[EXECUTOR] Action failed: {actionResult.Action}, attempting vision recovery...");
                    
                    // Attempt vision-based recovery
                    if (!string.IsNullOrEmpty(_currentGoal))
                    {
                        var recoveryResult = await _visionRecovery.AttemptRecoveryAsync(
                            _currentGoal, 
                            actionResult.Action, 
                            actionResult.Error ?? "unknown"
                        );
                        
                        if (recoveryResult.Success && recoveryResult.RecoveryAction != null)
                        {
                            Debug.WriteLine($"[EXECUTOR] Vision recovery suggested: {recoveryResult.RecoveryAction.Action}");
                            
                            // Execute recovery action
                            var recoveryExec = await ExecuteRecoveryAction(recoveryResult.RecoveryAction);
                            
                            if (recoveryExec.Success)
                            {
                                Debug.WriteLine("[EXECUTOR] Recovery successful! Continuing plan...");
                                result.ActionResults.Add(recoveryExec);
                                await GetInterActionDelay(recoveryExec.Action);
                                continue; // Continue with next step
                            }
                        }
                    }
                    
                    // Recovery failed or not available
                    Debug.WriteLine($"[EXECUTOR] Plan aborted due to failed action: {actionResult.Action}");
                    result.Success = false;
                    result.Error = $"Failed at action: {actionResult.Action}";
                    break;
                }

                // Smart delay between actions based on action type
                await GetInterActionDelay(actionResult.Action);
            }

            stopwatch.Stop();
            result.TotalExecutionTimeMs = (int)stopwatch.ElapsedMilliseconds;
            
            if (result.Error == null)
            {
                result.Success = true;
            }

            Debug.WriteLine($"[EXECUTOR] Plan completed: {result.ActionResults.Count} actions in {result.TotalExecutionTimeMs}ms");
            return result;
        }
        
        /// <summary>
        /// Handle known dialog types automatically.
        /// Returns true if dialog was handled, false if it needs vision recovery.
        /// </summary>
        private async Task<bool> HandleKnownDialogAsync(WindowsAutomation.DialogInfo dialogInfo)
        {
            Debug.WriteLine($"[EXECUTOR] HandleKnownDialogAsync: type={dialogInfo.Type}");
            
            switch (dialogInfo.Type)
            {
                case WindowsAutomation.DialogType.FileExists:
                    // File exists - click Yes to replace (most common user intent)
                    Debug.WriteLine("[EXECUTOR] ✅ Auto-handling: File exists → Click Yes to replace");
                    _automation.DismissDialogWithYes();
                    await Task.Delay(300);
                    return true;
                    
                case WindowsAutomation.DialogType.Confirmation:
                    // General confirmation - click Yes
                    if (dialogInfo.HasYesNo)
                    {
                        Debug.WriteLine("[EXECUTOR] ✅ Auto-handling: Confirmation → Click Yes");
                        _automation.DismissDialogWithYes();
                        await Task.Delay(300);
                        return true;
                    }
                    if (dialogInfo.HasOkCancel)
                    {
                        Debug.WriteLine("[EXECUTOR] ✅ Auto-handling: Confirmation → Press Enter for OK");
                        _automation.PressKey("enter");
                        await Task.Delay(300);
                        return true;
                    }
                    break;
                    
                case WindowsAutomation.DialogType.SaveAs:
                    // Save As dialog - we're already typing the filename, just continue
                    Debug.WriteLine("[EXECUTOR] ℹ️ Save As dialog detected - filename entry expected");
                    return true;  // Not an error, we're in the middle of saving
                    
                case WindowsAutomation.DialogType.Error:
                    // Error dialog - log but don't auto-dismiss (needs user attention)
                    Debug.WriteLine($"[EXECUTOR] ⚠️ Error dialog detected: {dialogInfo.Title}");
                    return false;  // Let vision recovery handle it
                    
                case WindowsAutomation.DialogType.Warning:
                    // Warning dialog - proceed with caution
                    Debug.WriteLine($"[EXECUTOR] ⚠️ Warning dialog - calling vision for decision");
                    return false;  // Let vision decide
                    
                case WindowsAutomation.DialogType.Unknown:
                default:
                    Debug.WriteLine("[EXECUTOR] ❓ Unknown dialog type - calling vision");
                    return false;
            }
            
            return false;
        }
        
        /// <summary>
        /// Execute a recovery action from vision analysis.
        /// </summary>
        private async Task<ExecutionResult> ExecuteRecoveryAction(RecoveryAction recovery)
        {
            Debug.WriteLine($"[EXECUTOR] Executing recovery: {recovery.Action}");
            var result = new ExecutionResult { Action = recovery.Action };
            
            try
            {
                switch (recovery.Action)
                {
                    case "click":
                        Debug.WriteLine($"[EXECUTOR] Recovery click: X={recovery.X}, Y={recovery.Y}");
                        if (recovery.X.HasValue && recovery.Y.HasValue && recovery.X > 0 && recovery.Y > 0)
                        {
                            Debug.WriteLine($"[EXECUTOR] Clicking at ({recovery.X}, {recovery.Y})");
                            _automation.Click(recovery.X.Value, recovery.Y.Value);
                            result.Success = true;
                        }
                        else
                        {
                            Debug.WriteLine("[EXECUTOR] Click skipped - no valid coordinates");
                            result.Error = "No valid coordinates for click";
                        }
                        break;
                        
                    case "type_text":
                        if (!string.IsNullOrEmpty(recovery.Content))
                        {
                            _automation.TypeIntoApp(recovery.Content);
                            result.Success = true;
                        }
                        break;
                        
                    case "press_key":
                        if (!string.IsNullOrEmpty(recovery.Content))
                        {
                            _automation.PressKey(recovery.Content);
                            result.Success = true;
                        }
                        break;
                        
                    case "open_app":
                        if (!string.IsNullOrEmpty(recovery.Target))
                        {
                            result.Success = _automation.OpenApplication(recovery.Target);
                        }
                        break;
                        
                    case "wait":
                        await Task.Delay(1000);
                        result.Success = true;
                        break;
                        
                    default:
                        result.Error = $"Unknown recovery action: {recovery.Action}";
                        break;
                }
            }
            catch (Exception ex)
            {
                result.Error = ex.Message;
            }
            
            return result;
        }

        private async Task<ExecutionResult> ExecuteSingleAction(string action, JsonElement step)
        {
            var result = new ExecutionResult { Action = action };

            switch (action)
            {
                // ===== APP CONTROL =====
                case "open_app":
                    if (step.TryGetProperty("target", out JsonElement targetEl))
                    {
                        string target = targetEl.GetString() ?? "";
                        result.Success = _automation.OpenApplication(target);
                        if (result.Success)
                        {
                            // Track the app for focusing before typing
                            _lastOpenedApp = target.Replace(".exe", "").Replace(".EXE", "");
                            Debug.WriteLine($"[EXECUTOR] Tracking last app: {_lastOpenedApp}");
                            // Wait for app window to be ready
                            await Task.Delay(500);
                        }
                    }
                    break;

                case "close_app":
                    if (step.TryGetProperty("target", out JsonElement closeEl))
                    {
                        _automation.CloseApplication(closeEl.GetString() ?? "");
                        result.Success = true;
                    }
                    break;

                // ===== TEXT INPUT =====
                case "type_text":
                    if (step.TryGetProperty("content", out JsonElement contentEl))
                    {
                        // Focus the last opened app before typing
                        if (!string.IsNullOrEmpty(_lastOpenedApp))
                        {
                            Debug.WriteLine($"[EXECUTOR] Focusing {_lastOpenedApp} before typing");
                            _automation.FocusWindow(_lastOpenedApp);
                            await Task.Delay(200);
                        }
                        _automation.TypeIntoApp(contentEl.GetString() ?? "");
                        result.Success = true;
                    }
                    break;

                case "navigate":
                    if (step.TryGetProperty("url", out JsonElement urlEl))
                    {
                        _automation.TypeIntoApp((urlEl.GetString() ?? "") + "\n");
                        result.Success = true;
                    }
                    break;

                case "search":
                case "search_web":
                    if (step.TryGetProperty("query", out JsonElement queryEl))
                    {
                        _automation.TypeIntoApp((queryEl.GetString() ?? "") + "\n");
                        result.Success = true;
                    }
                    break;

                // ===== VOLUME =====
                case "volume_up":
                    int volUp = (step.TryGetProperty("amount", out var amtUp) && amtUp.ValueKind == JsonValueKind.Number) 
                        ? amtUp.GetInt32() : 10;
                    _automation.VolumeUp(volUp / 2);
                    result.Success = true;
                    break;

                case "volume_down":
                    int volDown = (step.TryGetProperty("amount", out var amtDown) && amtDown.ValueKind == JsonValueKind.Number) 
                        ? amtDown.GetInt32() : 10;
                    _automation.VolumeDown(volDown / 2);
                    result.Success = true;
                    break;

                case "volume_mute":
                    _automation.VolumeMute();
                    result.Success = true;
                    break;

                // ===== BRIGHTNESS =====
                case "brightness_up":
                    int brUp = (step.TryGetProperty("amount", out var brUpAmt) && brUpAmt.ValueKind == JsonValueKind.Number) 
                        ? brUpAmt.GetInt32() : 10;
                    _automation.BrightnessUp(brUp);
                    result.Success = true;
                    break;

                case "brightness_down":
                    int brDown = (step.TryGetProperty("amount", out var brDownAmt) && brDownAmt.ValueKind == JsonValueKind.Number) 
                        ? brDownAmt.GetInt32() : 10;
                    _automation.BrightnessDown(brDown);
                    result.Success = true;
                    break;

                // ===== WINDOW =====
                case "minimize_window":
                    _automation.MinimizeWindow();
                    result.Success = true;
                    break;

                case "maximize_window":
                    _automation.MaximizeWindow();
                    result.Success = true;
                    break;

                case "restore_window":
                    _automation.RestoreWindow();
                    result.Success = true;
                    break;

                case "alt_tab":
                    _automation.AltTab();
                    result.Success = true;
                    break;

                case "show_desktop":
                    _automation.ShowDesktop();
                    result.Success = true;
                    break;

                // ===== KEYBOARD =====
                case "press_key":
                    if (step.TryGetProperty("content", out JsonElement keyEl))
                    {
                        _automation.PressKey(keyEl.GetString() ?? "");
                        result.Success = true;
                    }
                    break;

                case "hotkey":
                    if (step.TryGetProperty("content", out JsonElement hotkeyEl))
                    {
                        _automation.Hotkey(hotkeyEl.GetString() ?? "");
                        result.Success = true;
                    }
                    break;

                // ===== SYSTEM =====
                case "lock_screen":
                    _automation.LockScreen();
                    result.Success = true;
                    break;

                case "sleep":
                    _automation.Sleep();
                    result.Success = true;
                    break;

                case "shutdown":
                    _automation.Shutdown();
                    result.Success = true;
                    break;

                case "restart":
                    _automation.Restart();
                    result.Success = true;
                    break;

                case "screenshot":
                    _automation.TakeScreenshot();
                    result.Success = true;
                    break;

                // ===== CLIPBOARD =====
                case "copy":
                    _automation.Copy();
                    result.Success = true;
                    break;

                case "paste":
                    _automation.Paste();
                    result.Success = true;
                    break;

                case "cut":
                    _automation.Cut();
                    result.Success = true;
                    break;

                case "undo":
                    _automation.Undo();
                    result.Success = true;
                    break;

                case "redo":
                    _automation.Redo();
                    result.Success = true;
                    break;

                case "select_all":
                    _automation.SelectAll();
                    result.Success = true;
                    break;

                case "save":
                    _automation.Save();
                    result.Success = true;
                    break;

                // ===== WAIT / TIMING =====
                case "wait":
                    // Smart wait: check for specific duration or use intelligent default
                    int waitMs = 3000; // Default 3 seconds
                    if (step.TryGetProperty("duration", out var durEl))
                    {
                        waitMs = durEl.GetInt32() * 1000; // Convert seconds to ms
                    }
                    else if (step.TryGetProperty("ms", out var msEl))
                    {
                        waitMs = msEl.GetInt32();
                    }
                    Debug.WriteLine($"[EXECUTOR] Waiting {waitMs}ms");
                    await Task.Delay(waitMs);
                    result.Success = true;
                    break;

                case "smart_wait":
                case "wait_for_ready":
                    // Intelligent wait: check for window stability/ready state
                    string targetTitle = step.TryGetProperty("target", out var waitTarget) 
                        ? waitTarget.GetString() ?? "" : "";
                    int maxWaitMs = step.TryGetProperty("timeout", out var timeoutEl) 
                        ? timeoutEl.GetInt32() * 1000 : 10000; // Default 10s timeout
                    
                    Debug.WriteLine($"[EXECUTOR] Smart wait for '{targetTitle}' (max {maxWaitMs}ms)");
                    
                    // Poll for window stability
                    bool windowReady = false;
                    var startTime = DateTime.Now;
                    string lastTitle = "";
                    int stableCount = 0;
                    
                    while ((DateTime.Now - startTime).TotalMilliseconds < maxWaitMs)
                    {
                        var currentTitle = _visionRecovery.GetForegroundWindowTitle();
                        
                        // Check if title matches target (if specified)
                        if (!string.IsNullOrEmpty(targetTitle) && 
                            !currentTitle.ToLower().Contains(targetTitle.ToLower()))
                        {
                            stableCount = 0;
                            await Task.Delay(200);
                            continue;
                        }
                        
                        // Check for title stability (same title for 3 consecutive checks)
                        if (currentTitle == lastTitle)
                        {
                            stableCount++;
                            if (stableCount >= 3)
                            {
                                windowReady = true;
                                Debug.WriteLine($"[EXECUTOR] Window stable: '{currentTitle}'");
                                break;
                            }
                        }
                        else
                        {
                            stableCount = 0;
                            lastTitle = currentTitle;
                        }
                        
                        await Task.Delay(200);
                    }
                    
                    result.Success = windowReady;
                    result.Details = windowReady ? "Window ready" : "Timeout waiting for window";
                    break;

                // ===== MEDIA =====
                case "media_play_pause":
                    _automation.MediaPlayPause();
                    result.Success = true;
                    break;

                case "media_next":
                    _automation.MediaNext();
                    result.Success = true;
                    break;

                case "media_previous":
                    _automation.MediaPrevious();
                    result.Success = true;
                    break;

                case "media_stop":
                    _automation.MediaStop();
                    result.Success = true;
                    break;

                // ===== BROWSER =====
                case "new_tab":
                    _automation.NewTab();
                    result.Success = true;
                    break;

                case "close_tab":
                    _automation.CloseTab();
                    result.Success = true;
                    break;

                case "refresh":
                    _automation.Refresh();
                    result.Success = true;
                    break;

                case "go_back":
                    _automation.GoBack();
                    result.Success = true;
                    break;

                case "go_forward":
                    _automation.GoForward();
                    result.Success = true;
                    break;

                // ===== MOUSE =====
                case "click":
                    if (step.TryGetProperty("x", out var xEl) && step.TryGetProperty("y", out var yEl))
                    {
                        _automation.Click(xEl.GetInt32(), yEl.GetInt32());
                        result.Success = true;
                    }
                    break;

                case "double_click":
                    if (step.TryGetProperty("x", out var dxEl) && step.TryGetProperty("y", out var dyEl))
                    {
                        _automation.DoubleClick(dxEl.GetInt32(), dyEl.GetInt32());
                        result.Success = true;
                    }
                    break;

                case "right_click":
                    if (step.TryGetProperty("x", out var rxEl) && step.TryGetProperty("y", out var ryEl))
                    {
                        _automation.RightClick(rxEl.GetInt32(), ryEl.GetInt32());
                        result.Success = true;
                    }
                    break;

                case "move_mouse":
                    if (step.TryGetProperty("x", out var mxEl) && step.TryGetProperty("y", out var myEl))
                    {
                        _automation.MoveMouse(mxEl.GetInt32(), myEl.GetInt32());
                        result.Success = true;
                    }
                    break;

                case "scroll":
                    string dir = step.TryGetProperty("target", out var dirEl) ? dirEl.GetString() ?? "down" : "down";
                    _automation.Scroll(dir);
                    result.Success = true;
                    break;

                // ===== VIRTUAL DESKTOP =====
                case "switch_desktop_left":
                case "desktop_left":
                case "previous_desktop":
                    _automation.SwitchDesktopLeft();
                    result.Success = true;
                    break;

                case "switch_desktop_right":
                case "desktop_right":
                case "next_desktop":
                    _automation.SwitchDesktopRight();
                    result.Success = true;
                    break;

                case "new_desktop":
                case "create_desktop":
                    _automation.NewDesktop();
                    result.Success = true;
                    break;

                case "close_desktop":
                    _automation.CloseDesktop();
                    result.Success = true;
                    break;

                case "task_view":
                case "show_desktops":
                    _automation.TaskView();
                    result.Success = true;
                    break;

                // ===== YOUTUBE SHORTCUTS =====
                case "youtube_skip_ad":
                    // Skip ad: Tab to focus skip button, then Enter
                    _automation.PressKey("tab");
                    await Task.Delay(100);
                    _automation.PressKey("enter");
                    result.Success = true;
                    break;

                case "youtube_play":
                case "youtube_pause":
                    // Space or K toggles play/pause on YouTube
                    _automation.PressKey("space");
                    result.Success = true;
                    break;

                case "youtube_fullscreen":
                    // F key for fullscreen on YouTube
                    _automation.Hotkey("f");
                    result.Success = true;
                    break;

                case "youtube_next":
                    // Shift+N for next video on YouTube
                    _automation.Hotkey("shift+n");
                    result.Success = true;
                    break;

                // ===== UI AUTOMATION (Element-Based Actions) =====
                case "click_button":
                    if (step.TryGetProperty("target", out var btnTarget))
                    {
                        string buttonName = btnTarget.GetString() ?? "";
                        Debug.WriteLine($"[EXECUTOR] UI Automation: click_button '{buttonName}'");
                        var button = _uiFinder.FindButton(buttonName);
                        if (button != null)
                        {
                            result.Success = _uiFinder.ClickElement(button);
                        }
                        else
                        {
                            result.Error = $"Button not found: {buttonName}";
                        }
                    }
                    break;
                    
                case "click_menu":
                    if (step.TryGetProperty("path", out var menuPath))
                    {
                        string path = menuPath.GetString() ?? "";
                        Debug.WriteLine($"[EXECUTOR] UI Automation: click_menu '{path}'");
                        var menuItem = _uiFinder.FindMenuItem(path);
                        if (menuItem != null)
                        {
                            result.Success = _uiFinder.ClickElement(menuItem);
                        }
                        else
                        {
                            result.Error = $"Menu not found: {path}";
                        }
                    }
                    break;
                    
                case "click_element":
                case "find_and_click":
                    if (step.TryGetProperty("target", out var elemTarget))
                    {
                        string description = elemTarget.GetString() ?? "";
                        
                        // Check if vision targeting is required (ambiguous target like "any video")
                        bool requiresVision = step.TryGetProperty("requires_vision_targeting", out var rvt) && 
                                             rvt.ValueKind == JsonValueKind.True;
                        
                        Debug.WriteLine($"[EXECUTOR] click_element '{description}' (vision_required={requiresVision})");
                        
                        // OPTIMIZATION: Try UIElementFinder FIRST (free, fast, ~10ms)
                        // Only fall back to vision API if accessibility search fails
                        var element = _uiFinder.FindElement(description);
                        if (element != null)
                        {
                            Debug.WriteLine($"[EXECUTOR] UIElementFinder found '{description}' - clicking (fast path)");
                            result.Success = _uiFinder.ClickElement(element);
                            result.Details = "UIElementFinder (accessibility-based)";
                        }
                        else if (requiresVision)
                        {
                            // UIElementFinder failed, use vision API for ambiguous targets
                            Debug.WriteLine($"[EXECUTOR] UIElementFinder failed, using vision for: '{description}'");
                            var visionResult = await _visionRecovery.FindClickTargetAsync(description, _currentGoal);
                            
                            if (visionResult != null && visionResult.Success && visionResult.X > 0 && visionResult.Y > 0)
                            {
                                Debug.WriteLine($"[EXECUTOR] Vision found target at ({visionResult.X}, {visionResult.Y})");
                                _automation.Click(visionResult.X, visionResult.Y);
                                result.Success = true;
                                result.Details = $"Vision click at ({visionResult.X}, {visionResult.Y}): {visionResult.Element}";
                            }
                            else
                            {
                                result.Error = $"Both UIElementFinder and Vision failed to find: {description}";
                            }
                        }
                        else
                        {
                            // Not marked for vision, just report element not found
                            result.Error = $"Element not found via accessibility: {description}";
                        }
                    }
                    break;
                    
                case "type_in_element":
                    if (step.TryGetProperty("target", out var inputTarget) && 
                        step.TryGetProperty("content", out var inputContent))
                    {
                        string fieldName = inputTarget.GetString() ?? "";
                        string text = inputContent.GetString() ?? "";
                        Debug.WriteLine($"[EXECUTOR] UI Automation: type_in_element '{fieldName}' -> '{text}'");
                        var textBox = _uiFinder.FindTextBox(fieldName);
                        if (textBox != null)
                        {
                            result.Success = _uiFinder.TypeInElement(textBox, text);
                        }
                        else
                        {
                            result.Error = $"Text field not found: {fieldName}";
                        }
                    }
                    break;
                
                // Vision-guided execution (LLM planning fallback)
                case "vision_guided":
                    {
                        string goal = step.TryGetProperty("goal", out var goalEl) ? goalEl.GetString() ?? "" : _currentGoal;
                        Debug.WriteLine($"[EXECUTOR] Vision-guided execution for goal: '{goal}'");
                        
                        // Use vision recovery to analyze screen and get next action
                        var recovery = await _visionRecovery.AttemptRecoveryAsync(
                            goal, "vision_guided", "LLM planning failed");
                        
                        if (recovery.Success && recovery.RecoveryAction != null)
                        {
                            var recoveryStep = recovery.RecoveryAction;
                            Debug.WriteLine($"[EXECUTOR] Vision suggests: {recoveryStep.Action} at ({recoveryStep.X}, {recoveryStep.Y})");
                            
                            // Execute the vision-suggested action
                            if (recoveryStep.Action == "click" && recoveryStep.X.HasValue && recoveryStep.Y.HasValue)
                            {
                                _automation.Click(recoveryStep.X.Value, recoveryStep.Y.Value);
                                result.Success = true;
                                result.Details = $"Vision clicked at ({recoveryStep.X}, {recoveryStep.Y})";
                            }
                            else if (recoveryStep.Action == "type_text" && !string.IsNullOrEmpty(recoveryStep.Content))
                            {
                                _automation.TypeIntoApp(recoveryStep.Content);
                                result.Success = true;
                            }
                            else if (recoveryStep.Action == "none")
                            {
                                // Goal already achieved
                                result.Success = true;
                                result.Details = "Vision determined goal is already achieved";
                            }
                            else
                            {
                                result.Error = $"Unsupported vision action: {recoveryStep.Action}";
                            }
                        }
                        else
                        {
                            result.Error = recovery.Message ?? "Vision-guided execution failed";
                        }
                    }
                    break;
                    
                case "get_ui_elements":
                    // Debug action to list all available UI elements
                    Debug.WriteLine("[EXECUTOR] Getting all UI elements...");
                    var elements = _uiFinder.GetAllElements();
                    foreach (var elem in elements.Take(20))
                    {
                        Debug.WriteLine($"[UI] {elem.Type}: '{elem.Name}' ({elem.AutomationId})");
                    }
                    result.Success = true;
                    break;

                // ===== SKILL RECORDING & PLAYBACK =====
                case "start_recording":
                    if (step.TryGetProperty("target", out var skillNameEl))
                    {
                        string skillName = skillNameEl.GetString() ?? "unnamed_skill";
                        Debug.WriteLine($"[EXECUTOR] 🔴 Starting skill recording: {skillName}");
                        SkillRecorder.Instance.StartRecording(skillName);
                        result.Success = true;
                    }
                    else
                    {
                        SkillRecorder.Instance.StartRecording($"skill_{DateTime.Now:yyyyMMdd_HHmmss}");
                        result.Success = true;
                    }
                    break;
                    
                case "stop_recording":
                    Debug.WriteLine("[EXECUTOR] ⏹ Stopping skill recording");
                    var savedSkill = SkillRecorder.Instance.StopRecording(true);
                    result.Success = savedSkill != null;
                    if (savedSkill != null)
                    {
                        Debug.WriteLine($"[EXECUTOR] Saved skill: {savedSkill.Name} with {savedSkill.Actions.Count} actions");
                    }
                    break;
                    
                case "play_skill":
                    if (step.TryGetProperty("target", out var playSkillName))
                    {
                        string skillToPlay = playSkillName.GetString() ?? "";
                        Debug.WriteLine($"[EXECUTOR] ▶ Playing skill: {skillToPlay}");
                        var skill = SkillRecorder.Instance.FindSkill(skillToPlay);
                        if (skill != null)
                        {
                            // Play the skill (async)
                            await SkillRecorder.Instance.PlaySkillAsync(skill.Name);
                            result.Success = true;
                        }
                        else
                        {
                            result.Error = $"Skill not found: {skillToPlay}";
                            Debug.WriteLine($"[EXECUTOR] Skill not found: {skillToPlay}");
                        }
                    }
                    break;
                    
                case "list_skills":
                    Debug.WriteLine("[EXECUTOR] Listing all skills...");
                    var allSkills = SkillRecorder.Instance.GetAllSkills();
                    foreach (var s in allSkills)
                    {
                        Debug.WriteLine($"[SKILL] {s.Name}: {s.ActionCount} actions, used {s.UseCount}x");
                    }
                    result.Success = true;
                    break;

                default:
                    result.Success = false;
                    result.Error = $"Unknown action: {action}";
                    break;
            }

            // ==== SKILL RECORDING HOOK ====
            // If SkillRecorder is actively recording, capture this action
            // Skip skill management actions - don't record start/stop/play commands
            var skipActions = new[] { "start_recording", "stop_recording", "play_skill", "list_skills" };
            if (result.Success && SkillRecorder.Instance.IsRecording && !skipActions.Contains(action))
            {
                var parameters = new System.Collections.Generic.Dictionary<string, object>
                {
                    { "action", action }
                };
                
                // Capture relevant parameters based on action type (with null checks)
                if (step.TryGetProperty("target", out var t) && t.ValueKind == JsonValueKind.String) 
                    parameters["target"] = t.GetString() ?? "";
                if (step.TryGetProperty("content", out var c) && c.ValueKind == JsonValueKind.String) 
                    parameters["content"] = c.GetString() ?? "";
                if (step.TryGetProperty("url", out var u) && u.ValueKind == JsonValueKind.String) 
                    parameters["url"] = u.GetString() ?? "";
                if (step.TryGetProperty("x", out var x) && x.ValueKind == JsonValueKind.Number) 
                    parameters["x"] = x.GetInt32();
                if (step.TryGetProperty("y", out var y) && y.ValueKind == JsonValueKind.Number) 
                    parameters["y"] = y.GetInt32();
                if (step.TryGetProperty("amount", out var a) && a.ValueKind == JsonValueKind.Number) 
                    parameters["amount"] = a.GetInt32();
                
                SkillRecorder.Instance.RecordAction(action, parameters);
                Debug.WriteLine($"[EXECUTOR] Recorded to skill: {action}");
            }

            return result;
        }

        /// <summary>
        /// Smart delay based on action type - ensures proper timing between actions.
        /// </summary>
        private async Task GetInterActionDelay(string action)
        {
            int delayMs = action switch
            {
                "open_app" => 1500,      // Apps need time to load
                "navigate" => 1500,      // Page needs to load
                "search" or "search_web" => 1500,
                "type_text" => 200,      // Small delay after typing
                "click" or "double_click" => 300,
                _ => BASE_DELAY_MS       // Default delay
            };

            await Task.Delay(delayMs);
        }
    }

    /// <summary>
    /// Result of a single action execution.
    /// </summary>
    public class ExecutionResult
    {
        public bool Success { get; set; }
        public string Action { get; set; } = "";
        public string? Error { get; set; }
        public string? Details { get; set; }  // Additional info like vision click coords
        public int ExecutionTimeMs { get; set; }
    }

    /// <summary>
    /// Result of executing an entire plan.
    /// </summary>
    public class PlanExecutionResult
    {
        public bool Success { get; set; }
        public string? Error { get; set; }
        public int TotalExecutionTimeMs { get; set; }
        public System.Collections.Generic.List<ExecutionResult> ActionResults { get; set; } = new();
    }
    
    /// <summary>
    /// Recovery action from vision analysis.
    /// </summary>
    public class RecoveryAction
    {
        public string Action { get; set; } = "";
        public int? X { get; set; }
        public int? Y { get; set; }
        public string? Content { get; set; }
        public string? Target { get; set; }
        public string? Reasoning { get; set; }
    }
    
    /// <summary>
    /// Result of vision recovery attempt.
    /// </summary>
    public class VisionRecoveryResult
    {
        public bool Success { get; set; }
        public bool RecoveryPossible { get; set; }
        public RecoveryAction? RecoveryAction { get; set; }
        public string? CurrentState { get; set; }
        public string? Blocker { get; set; }
        public double? Confidence { get; set; }
        public string? Message { get; set; }
    }
    
    /// <summary>
    /// Result of vision-based click target finding.
    /// </summary>
    public class ClickTargetResult
    {
        public bool Success { get; set; }
        public int X { get; set; }
        public int Y { get; set; }
        public string? Element { get; set; }
        public double Confidence { get; set; }
    }
    
    /// <summary>
    /// Service to call Python vision recovery API.
    /// Uses Gemini Vision to analyze screen and suggest recovery actions.
    /// </summary>
    public class VisionRecoveryService
    {
        private readonly string _recoveryUrl = "http://localhost:8000/api/agent/recover";
        private readonly HttpClient _client;
        
        public VisionRecoveryService()
        {
            _client = new HttpClient();
            _client.Timeout = TimeSpan.FromSeconds(60);  // Increased for Gemma 3
        }
        
        /// <summary>
        /// Call the vision recovery API to get suggested recovery action.
        /// Now includes execution context for smarter vision analysis.
        /// </summary>
        public async Task<VisionRecoveryResult> AttemptRecoveryAsync(
            string originalCommand, 
            string failedAction, 
            string errorReason,
            string focusedWindow = "",
            string focusedProcess = "",
            string[]? openedApps = null,
            int stepNumber = 0,
            int totalSteps = 0,
            string lastAction = "",
            bool lastResult = true)
        {
            try
            {
                // Get currently focused window if not provided
                if (string.IsNullOrEmpty(focusedWindow))
                {
                    focusedWindow = GetForegroundWindowTitle();
                    focusedProcess = GetForegroundProcessName();
                }
                
                Debug.WriteLine($"[VISION] Requesting recovery for: {failedAction}");
                Debug.WriteLine($"[VISION] Context: Focused={focusedWindow}, Step={stepNumber}");
                
                var requestBody = new
                {
                    original_command = originalCommand,
                    failed_action = failedAction,
                    error_reason = errorReason,
                    // Context for Vision
                    focused_window = focusedWindow,
                    focused_process = focusedProcess,
                    opened_apps = openedApps ?? Array.Empty<string>(),
                    step_number = stepNumber,
                    total_steps = totalSteps,
                    last_action = lastAction,
                    last_result = lastResult
                };
                
                var json = JsonSerializer.Serialize(requestBody);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                
                var response = await _client.PostAsync(_recoveryUrl, content);
                
                if (!response.IsSuccessStatusCode)
                {
                    Debug.WriteLine($"[VISION] Recovery API error: {response.StatusCode}");
                    return new VisionRecoveryResult { Success = false, Message = $"API error: {response.StatusCode}" };
                }
                
                var responseJson = await response.Content.ReadAsStringAsync();
                Debug.WriteLine($"[VISION] Recovery response: {responseJson}");
                
                using var doc = JsonDocument.Parse(responseJson);
                var root = doc.RootElement;
                
                var result = new VisionRecoveryResult
                {
                    Success = root.TryGetProperty("success", out var s) && s.GetBoolean(),
                    RecoveryPossible = root.TryGetProperty("recovery_possible", out var rp) && rp.GetBoolean(),
                    CurrentState = root.TryGetProperty("current_state", out var cs) ? cs.GetString() : null,
                    Blocker = root.TryGetProperty("blocker", out var b) ? b.GetString() : null,
                    Confidence = root.TryGetProperty("confidence", out var c) ? c.GetDouble() : null,
                    Message = root.TryGetProperty("message", out var m) ? m.GetString() : null
                };
                
                // Parse recovery action if present
                if (root.TryGetProperty("recovery_action", out var ra) && ra.ValueKind != JsonValueKind.Null)
                {
                    int? xVal = null, yVal = null;
                    try { if (ra.TryGetProperty("x", out var x) && x.ValueKind == JsonValueKind.Number) xVal = x.GetInt32(); } catch { }
                    try { if (ra.TryGetProperty("y", out var y) && y.ValueKind == JsonValueKind.Number) yVal = y.GetInt32(); } catch { }
                    
                    result.RecoveryAction = new RecoveryAction
                    {
                        Action = ra.TryGetProperty("action", out var a) ? a.GetString() ?? "" : "",
                        X = xVal,
                        Y = yVal,
                        Content = ra.TryGetProperty("content", out var ct) ? ct.GetString() : null,
                        Target = ra.TryGetProperty("target", out var t) ? t.GetString() : null,
                        Reasoning = ra.TryGetProperty("reasoning", out var r) ? r.GetString() : null
                    };
                    Debug.WriteLine($"[VISION] Parsed recovery: action={result.RecoveryAction.Action} x={xVal} y={yVal}");
                }
                
                return result;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[VISION] Recovery error: {ex.Message}");
                return new VisionRecoveryResult { Success = false, Message = ex.Message };
            }
        }
        
        /// <summary>
        /// Find a clickable target using vision analysis.
        /// Called when a step has requires_vision_targeting=true.
        /// </summary>
        public async Task<ClickTargetResult?> FindClickTargetAsync(string targetDescription, string goal = "")
        {
            try
            {
                Debug.WriteLine($"[VISION-TARGET] Finding target: '{targetDescription}'");
                
                // Capture screenshot
                var screenshot = CaptureScreenshotBase64();
                if (string.IsNullOrEmpty(screenshot))
                {
                    Debug.WriteLine("[VISION-TARGET] Failed to capture screenshot");
                    return null;
                }
                
                var requestBody = new
                {
                    screenshot = screenshot,
                    target = targetDescription,
                    goal = goal
                };
                
                var json = JsonSerializer.Serialize(requestBody);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                
                var response = await _client.PostAsync("http://localhost:8000/api/vision/find-target", content);
                
                if (!response.IsSuccessStatusCode)
                {
                    Debug.WriteLine($"[VISION-TARGET] API error: {response.StatusCode}");
                    return null;
                }
                
                var responseJson = await response.Content.ReadAsStringAsync();
                Debug.WriteLine($"[VISION-TARGET] Response: {responseJson}");
                
                using var doc = JsonDocument.Parse(responseJson);
                var root = doc.RootElement;
                
                if (root.TryGetProperty("success", out var success) && success.GetBoolean())
                {
                    var result = new ClickTargetResult
                    {
                        Success = true,
                        X = root.TryGetProperty("x", out var x) ? x.GetInt32() : 0,
                        Y = root.TryGetProperty("y", out var y) ? y.GetInt32() : 0,
                        Element = root.TryGetProperty("element", out var elem) ? elem.GetString() : "",
                        Confidence = root.TryGetProperty("confidence", out var conf) ? conf.GetDouble() : 0
                    };
                    
                    Debug.WriteLine($"[VISION-TARGET] Found at ({result.X}, {result.Y}) - {result.Element}");
                    return result;
                }
                
                Debug.WriteLine("[VISION-TARGET] Target not found");
                return null;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[VISION-TARGET] Error: {ex.Message}");
                return null;
            }
        }
        
        /// <summary>
        /// Capture screenshot and convert to base64.
        /// </summary>
        private string CaptureScreenshotBase64()
        {
            try
            {
                var bounds = System.Windows.Forms.Screen.PrimaryScreen.Bounds;
                using var bitmap = new System.Drawing.Bitmap(bounds.Width, bounds.Height);
                using var graphics = System.Drawing.Graphics.FromImage(bitmap);
                graphics.CopyFromScreen(System.Drawing.Point.Empty, System.Drawing.Point.Empty, bounds.Size);
                
                using var ms = new System.IO.MemoryStream();
                bitmap.Save(ms, System.Drawing.Imaging.ImageFormat.Png);
                return Convert.ToBase64String(ms.ToArray());
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[VISION-TARGET] Screenshot error: {ex.Message}");
                return "";
            }
        }
        
        // P/Invoke for getting foreground window
        [System.Runtime.InteropServices.DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();
        
        [System.Runtime.InteropServices.DllImport("user32.dll")]
        private static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
        
        [System.Runtime.InteropServices.DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
        
        public string GetForegroundWindowTitle()
        {
            try
            {
                IntPtr hWnd = GetForegroundWindow();
                var sb = new System.Text.StringBuilder(256);
                if (GetWindowText(hWnd, sb, 256) > 0)
                {
                    return sb.ToString();
                }
            }
            catch { }
            return "";
        }
        
        private string GetForegroundProcessName()
        {
            try
            {
                IntPtr hWnd = GetForegroundWindow();
                GetWindowThreadProcessId(hWnd, out uint processId);
                var process = System.Diagnostics.Process.GetProcessById((int)processId);
                return process.ProcessName;
            }
            catch { }
            return "";
        }
    }
}
