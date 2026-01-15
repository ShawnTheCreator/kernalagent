using System;
using System.Threading.Tasks;
using System.Diagnostics;
using System.Text.Json;
using System.Net.Http;
using System.Text;

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
        private const int MAX_RETRIES = 3;
        private const int BASE_DELAY_MS = 100;
        private string _currentGoal = "";  // Track original command for recovery
        
        public SmartExecutor()
        {
            _automation = new WindowsAutomation();
            _visionRecovery = new VisionRecoveryService();
        }
        
        public void SetOriginalGoal(string goal)
        {
            _currentGoal = goal;
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
        /// </summary>
        public async Task<PlanExecutionResult> ExecutePlanAsync(JsonElement stepsElement)
        {
            var result = new PlanExecutionResult();
            var stopwatch = Stopwatch.StartNew();

            foreach (var step in stepsElement.EnumerateArray())
            {
                var actionResult = await ExecuteActionAsync(step);
                result.ActionResults.Add(actionResult);
                
                // Get action name for proactive checks
                string actionName = "";
                if (step.TryGetProperty("action", out var actionEl))
                    actionName = actionEl.GetString() ?? "";

                // PROACTIVE VISION CHECK for open_app (even if "succeeded")
                // Chrome profile picker, UAC dialogs, etc. may block progress
                if (actionResult.Success && actionName == "open_app" && !string.IsNullOrEmpty(_currentGoal))
                {
                    Debug.WriteLine("[EXECUTOR] Proactive vision check after open_app...");
                    await Task.Delay(1500); // Wait for any dialogs to appear
                    
                    var proactiveCheck = await _visionRecovery.AttemptRecoveryAsync(
                        _currentGoal,
                        "verify_app_ready",
                        "proactive_check"
                    );
                    
                    // If vision found a blocker and suggests action
                    if (proactiveCheck.Success && proactiveCheck.RecoveryAction != null)
                    {
                        Debug.WriteLine($"[EXECUTOR] Vision found blocker: {proactiveCheck.Blocker}");
                        Debug.WriteLine($"[EXECUTOR] Vision suggests: {proactiveCheck.RecoveryAction.Action}");
                        
                        var recoveryExec = await ExecuteRecoveryAction(proactiveCheck.RecoveryAction);
                        if (recoveryExec.Success)
                        {
                            Debug.WriteLine("[EXECUTOR] Blocker cleared! Continuing...");
                            result.ActionResults.Add(recoveryExec);
                            await Task.Delay(500);
                        }
                    }
                }

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
                        if (recovery.X.HasValue && recovery.Y.HasValue)
                        {
                            _automation.Click(recovery.X.Value, recovery.Y.Value);
                            result.Success = true;
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
                    int volUp = step.TryGetProperty("amount", out var amtUp) ? amtUp.GetInt32() : 10;
                    _automation.VolumeUp(volUp / 2);
                    result.Success = true;
                    break;

                case "volume_down":
                    int volDown = step.TryGetProperty("amount", out var amtDown) ? amtDown.GetInt32() : 10;
                    _automation.VolumeDown(volDown / 2);
                    result.Success = true;
                    break;

                case "volume_mute":
                    _automation.VolumeMute();
                    result.Success = true;
                    break;

                // ===== BRIGHTNESS =====
                case "brightness_up":
                    int brUp = step.TryGetProperty("amount", out var brUpAmt) ? brUpAmt.GetInt32() : 10;
                    _automation.BrightnessUp(brUp);
                    result.Success = true;
                    break;

                case "brightness_down":
                    int brDown = step.TryGetProperty("amount", out var brDownAmt) ? brDownAmt.GetInt32() : 10;
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

                default:
                    result.Success = false;
                    result.Error = $"Unknown action: {action}";
                    break;
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
            _client.Timeout = TimeSpan.FromSeconds(30);
        }
        
        /// <summary>
        /// Call the vision recovery API to get suggested recovery action.
        /// </summary>
        public async Task<VisionRecoveryResult> AttemptRecoveryAsync(
            string originalCommand, 
            string failedAction, 
            string errorReason)
        {
            try
            {
                Debug.WriteLine($"[VISION] Requesting recovery for: {failedAction}");
                
                var requestBody = new
                {
                    original_command = originalCommand,
                    failed_action = failedAction,
                    error_reason = errorReason
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
                    result.RecoveryAction = new RecoveryAction
                    {
                        Action = ra.TryGetProperty("action", out var a) ? a.GetString() ?? "" : "",
                        X = ra.TryGetProperty("x", out var x) ? x.GetInt32() : null,
                        Y = ra.TryGetProperty("y", out var y) ? y.GetInt32() : null,
                        Content = ra.TryGetProperty("content", out var ct) ? ct.GetString() : null,
                        Target = ra.TryGetProperty("target", out var t) ? t.GetString() : null,
                        Reasoning = ra.TryGetProperty("reasoning", out var r) ? r.GetString() : null
                    };
                }
                
                return result;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[VISION] Recovery error: {ex.Message}");
                return new VisionRecoveryResult { Success = false, Message = ex.Message };
            }
        }
    }
}
