using System;
using System.Threading;
using System.Threading.Tasks;
using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Net.Http;
using System.Text;
using System.Linq;
using System.Windows.Automation;
using System.Drawing;
using System.IO;

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
        private const double RECOVERY_CONFIDENCE_THRESHOLD = 0.8;
        private string _currentGoal = "";  // Track original command for recovery
        private string _lastOpenedApp = ""; // Track last opened app for focus before typing
        private double? _planConfidence = null;
        private static readonly SemaphoreSlim _executionLock = new SemaphoreSlim(1, 1); // Prevent concurrent automation

        private const int DEFAULT_EXPECT_TIMEOUT_MS = 4000;

        private int GetStepTimeoutMs(JsonElement step, string actionName)
        {
            try
            {
                if (step.TryGetProperty("timeout_ms", out var toMsEl) && toMsEl.ValueKind == JsonValueKind.Number)
                {
                    try
                    {
                        var ms = toMsEl.GetInt32();
                        if (ms > 0)
                            return ms;
                    }
                    catch
                    {
                    }
                }

                if (step.TryGetProperty("step_timeout_ms", out var stMsEl) && stMsEl.ValueKind == JsonValueKind.Number)
                {
                    try
                    {
                        var ms = stMsEl.GetInt32();
                        if (ms > 0)
                            return ms;
                    }
                    catch
                    {
                    }
                }

                var a = (actionName ?? "").Trim().ToLowerInvariant();

                return a switch
                {
                    "open_app" => 20000,
                    "search" or "search_web" => 20000,
                    "click_element" or "find_and_click" => 25000,
                    "click_button" or "click_menu" => 20000,
                    "type" or "type_text" => 20000,
                    "smart_wait" or "wait_for_ready" => 20000,
                    "wait" => 60000,
                    _ => 30000
                };
            }
            catch
            {
                return 30000;
            }
        }

        private enum VisionMode
        {
            All,
            Off,
            BrowserOnly,
            NonBrowserOnly
        }

        private string GetSessionId()
        {
            try
            {
                return SettingsService.Instance.SessionId;
            }
            catch
            {
                return "";
            }
        }

        private static VisionMode? _visionMode;
        
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

        public void SetPlanConfidence(double? confidence)
        {
            _planConfidence = confidence;
        }

        private bool ShouldAttemptRecovery()
        {
            if (!IsVisionAllowed())
            {
                return false;
            }

            if (string.IsNullOrEmpty(_currentGoal))
            {
                return false;
            }

            // Skip recovery if LLM confidence was high (>0.85)
            if (_planConfidence > 0.85)
            {
                Debug.WriteLine($"[EXECUTOR] Skipping recovery due to high plan confidence: {_planConfidence:F2}");
                return false;
            }

            return true;
        }

        private static VisionMode GetVisionMode()
        {
            if (_visionMode.HasValue)
            {
                return _visionMode.Value;
            }

            var raw = Environment.GetEnvironmentVariable("VISION_MODE")?.Trim();
            if (string.IsNullOrWhiteSpace(raw))
            {
                _visionMode = VisionMode.All;
                return _visionMode.Value;
            }

            raw = raw.ToLowerInvariant();
            _visionMode = raw switch
            {
                "off" => VisionMode.Off,
                "browser_only" => VisionMode.BrowserOnly,
                "non_browser_only" => VisionMode.NonBrowserOnly,
                "all" => VisionMode.All,
                _ => VisionMode.All
            };
            return _visionMode.Value;
        }

        private bool IsVisionAllowed()
        {
            try
            {
                _context.RefreshContext();
                var mode = GetVisionMode();
                return mode switch
                {
                    VisionMode.Off => false,
                    VisionMode.BrowserOnly => _context.ActiveAppType == ContextManager.AppType.Browser,
                    VisionMode.NonBrowserOnly => _context.ActiveAppType != ContextManager.AppType.Browser,
                    _ => true,
                };
            }
            catch
            {
                return false;
            }
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
                            
                            // NEW: Log to Episodic Memory Timeline
                            await ApiService.Instance.LogTimelineEventAsync(
                                type: "action_tool", 
                                content: $"Executed: {action} {target}", 
                                metadata: new System.Collections.Generic.Dictionary<string, object> 
                                { 
                                    { "action", action },
                                    { "target", target },
                                    { "duration_ms", result.ExecutionTimeMs }
                                }
                            );
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
            return await ExecutePlanAsync(stepsElement, null);
        }

        public async Task<PlanExecutionResult> ExecutePlanAsync(
            JsonElement stepsElement,
            Action<int, int, string, string>? onStepProgress
        )
        {
            // Acquire lock to prevent concurrent automation
            await _executionLock.WaitAsync();
            try
            {
                return await ExecutePlanInternalAsync(stepsElement, onStepProgress);
            }
            finally
            {
                _executionLock.Release();
            }
        }

        private async Task<PlanExecutionResult> ExecutePlanInternalAsync(
            JsonElement stepsElement,
            Action<int, int, string, string>? onStepProgress
        )
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
                // ===== SECURITY VAULT GUARDRAILS (active window checks) =====
                try
                {
                    var decision = SecurityPolicyService.Instance.EvaluateCurrentContext(_context);
                    if (!decision.IsAllowed)
                    {
                        Debug.WriteLine($"[SECURITY] Blocked plan execution: {decision.Reason}");
                        result.Success = false;
                        result.Error = decision.Reason ?? "Blocked by Security Vault";
                        break;
                    }
                }
                catch
                {
                }

                stepIndex++;

                string stepActionNameForTimeout = "";
                try
                {
                    if (step.TryGetProperty("action", out var aEl))
                        stepActionNameForTimeout = aEl.GetString() ?? "";
                }
                catch
                {
                }

                try
                {
                    string stepAction = step.TryGetProperty("action", out var sa) ? (sa.GetString() ?? "") : "";
                    string stepTarget = "";
                    if (step.TryGetProperty("target", out var st))
                        stepTarget = st.GetString() ?? "";
                    if (string.IsNullOrWhiteSpace(stepTarget) && step.TryGetProperty("content", out var sc))
                        stepTarget = sc.GetString() ?? "";
                    onStepProgress?.Invoke(stepIndex, totalSteps, stepAction, stepTarget);
                }
                catch
                {
                }

                ExecutionResult actionResult;
                var stepTimeoutMs = GetStepTimeoutMs(step, stepActionNameForTimeout);
                var actionTask = ExecuteActionAsync(step);
                var completed = await Task.WhenAny(actionTask, Task.Delay(stepTimeoutMs));
                if (completed != actionTask)
                {
                    actionResult = new ExecutionResult
                    {
                        Success = false,
                        Action = stepActionNameForTimeout,
                        Error = $"Step timeout after {stepTimeoutMs}ms"
                    };
                }
                else
                {
                    actionResult = await actionTask;
                }
                result.ActionResults.Add(actionResult);

                // ===== EXPECTED OUTCOME VERIFICATION (Option B) =====
                if (actionResult.Success)
                {
                    var verified = await VerifyExpectedAsync(step, actionResult.Action);
                    if (!verified)
                    {
                        Debug.WriteLine($"[EXECUTOR] Expected outcome verification failed for: {actionResult.Action} - retrying once...");

                        // Retry once (same step) before considering recovery/abort
                        var retryResult = await ExecuteActionAsync(step);
                        result.ActionResults.Add(retryResult);

                        if (retryResult.Success)
                        {
                            var verifiedRetry = await VerifyExpectedAsync(step, retryResult.Action);
                            if (!verifiedRetry)
                            {
                                Debug.WriteLine($"[EXECUTOR] Verification failed after retry: {retryResult.Action}");
                                retryResult.Success = false;
                                retryResult.Error = "Expected outcome not met";
                                actionResult = retryResult;
                            }
                        }
                        else
                        {
                            actionResult = retryResult;
                        }
                    }
                }
                
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
                            
                            if (!string.IsNullOrEmpty(_currentGoal) && ShouldAttemptRecovery())
                            {
                                _context.RefreshContext();
                                var openedApps = string.IsNullOrEmpty(_lastOpenedApp) ? Array.Empty<string>() : new[] { _lastOpenedApp };
                                var recoveryResult = await _visionRecovery.AttemptRecoveryAsync(
                                    _currentGoal,
                                    actionName,
                                    $"Dialog appeared: {dialogInfo.Title}",
                                    dialogInfo.Title,
                                    _context.ActiveProcessName,
                                    openedApps,
                                    stepIndex,
                                    totalSteps,
                                    actionName,
                                    true,
                                    GetSessionId()
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
                    if (!string.IsNullOrEmpty(_currentGoal) && ShouldAttemptRecovery())
                    {
                        _context.RefreshContext();
                        var openedApps = string.IsNullOrEmpty(_lastOpenedApp) ? Array.Empty<string>() : new[] { _lastOpenedApp };
                        var recoveryResult = await _visionRecovery.AttemptRecoveryAsync(
                            _currentGoal,
                            actionResult.Action,
                            actionResult.Error ?? "unknown",
                            _context.ActiveWindowTitle,
                            _context.ActiveProcessName,
                            openedApps,
                            stepIndex,
                            totalSteps,
                            actionResult.Action,
                            false,
                            GetSessionId()
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

        private async Task<bool> VerifyExpectedAsync(JsonElement step, string actionName)
        {
            try
            {
                if (!step.TryGetProperty("expected", out var expectedEl) || expectedEl.ValueKind != JsonValueKind.Object)
                {
                    return true; // Backward compatible: no expected -> no verification
                }

                int timeoutMs = DEFAULT_EXPECT_TIMEOUT_MS;
                if (expectedEl.TryGetProperty("timeout_ms", out var toEl) && toEl.ValueKind == JsonValueKind.Number)
                {
                    try { timeoutMs = toEl.GetInt32(); } catch { }
                }

                var deadline = DateTime.UtcNow.AddMilliseconds(timeoutMs);

                while (DateTime.UtcNow < deadline)
                {
                    if (CheckExpectedOnce(expectedEl))
                        return true;

                    await Task.Delay(200);
                }

                return CheckExpectedOnce(expectedEl);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[EXECUTOR] VerifyExpectedAsync error: {ex.Message}");
                return true; // Do not hard-fail execution due to verifier exceptions
            }
        }

        private bool CheckExpectedOnce(JsonElement expectedEl)
        {
            try
            {
                // 1) Window title expectations
                if (expectedEl.TryGetProperty("window_title_contains", out var wtEl) && wtEl.ValueKind == JsonValueKind.String)
                {
                    var expected = wtEl.GetString() ?? "";
                    if (!string.IsNullOrWhiteSpace(expected))
                    {
                        var current = _visionRecovery.GetForegroundWindowTitle() ?? "";
                        if (!current.ToLowerInvariant().Contains(expected.ToLowerInvariant()))
                            return false;
                    }
                }

                if (expectedEl.TryGetProperty("window_title_not_contains", out var wtnEl) && wtnEl.ValueKind == JsonValueKind.String)
                {
                    var notExpected = wtnEl.GetString() ?? "";
                    if (!string.IsNullOrWhiteSpace(notExpected))
                    {
                        var current = _visionRecovery.GetForegroundWindowTitle() ?? "";
                        if (current.ToLowerInvariant().Contains(notExpected.ToLowerInvariant()))
                            return false;
                    }
                }

                // 2) Element expectations (UIA)
                if (expectedEl.TryGetProperty("element_present", out var epEl) && epEl.ValueKind == JsonValueKind.String)
                {
                    var name = epEl.GetString() ?? "";
                    if (!string.IsNullOrWhiteSpace(name))
                    {
                        var elem = _uiFinder.FindElement(name);
                        if (elem == null)
                            return false;
                    }
                }

                if (expectedEl.TryGetProperty("element_not_present", out var enpEl) && enpEl.ValueKind == JsonValueKind.String)
                {
                    var name = enpEl.GetString() ?? "";
                    if (!string.IsNullOrWhiteSpace(name))
                    {
                        var elem = _uiFinder.FindElement(name);
                        if (elem != null)
                            return false;
                    }
                }

                // 3) Textbox value expectation (best-effort)
                if (expectedEl.TryGetProperty("textbox_value_contains", out var tvEl) && tvEl.ValueKind == JsonValueKind.String)
                {
                    var expectedText = tvEl.GetString() ?? "";
                    if (!string.IsNullOrWhiteSpace(expectedText))
                    {
                        var focused = AutomationElement.FocusedElement;
                        if (focused != null && focused.TryGetCurrentPattern(ValuePattern.Pattern, out object vp))
                        {
                            var actual = ((ValuePattern)vp).Current.Value ?? "";
                            if (!actual.ToLowerInvariant().Contains(expectedText.ToLowerInvariant()))
                                return false;
                        }
                        else
                        {
                            // Can't read value -> treat as not verifiable right now
                            return true;
                        }
                    }
                }

                // 4) Focus expectation (best-effort)
                if (expectedEl.TryGetProperty("focused_element_name_contains", out var fnEl) && fnEl.ValueKind == JsonValueKind.String)
                {
                    var expectedName = fnEl.GetString() ?? "";
                    if (!string.IsNullOrWhiteSpace(expectedName))
                    {
                        var focused = AutomationElement.FocusedElement;
                        var actualName = focused != null ? (focused.Current.Name ?? "") : "";
                        if (!actualName.ToLowerInvariant().Contains(expectedName.ToLowerInvariant()))
                            return false;
                    }
                }

                // 5) Toggle state expectation (Quick Settings)
                if (expectedEl.TryGetProperty("toggle_state", out var tsEl) && tsEl.ValueKind == JsonValueKind.String)
                {
                    var desired = (tsEl.GetString() ?? "").Trim().ToLowerInvariant();
                    if (desired == "on" || desired == "off")
                    {
                        var targetName = "";
                        if (expectedEl.TryGetProperty("toggle_target", out var ttEl) && ttEl.ValueKind == JsonValueKind.String)
                            targetName = ttEl.GetString() ?? "";

                        if (string.IsNullOrWhiteSpace(targetName))
                            return true; // can't locate target

                        var toggle = _uiFinder.FindButton(targetName) ?? _uiFinder.FindElement(targetName);
                        if (toggle == null)
                            return false;

                        var state = _uiFinder.GetToggleState(toggle);
                        if (state.HasValue)
                        {
                            bool isOn = state.Value == ToggleState.On;
                            bool wantOn = desired == "on";
                            if (isOn != wantOn)
                                return false;
                        }
                    }
                }

                return true;
            }
            catch
            {
                return true;
            }
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

                    case "none":
                        result.Success = true;
                        result.Details = "Recovery not needed";
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

                        try
                        {
                            if (SecurityPolicyService.Instance.IsBlockedTargetApp(target))
                            {
                                result.Success = false;
                                result.Error = $"Security Vault blocked opening restricted app: {target}";
                                break;
                            }
                        }
                        catch
                        {
                        }

                        result.Success = _automation.OpenApplication(target);
                        if (result.Success)
                        {
                            // Track the app for focusing before typing
                            _lastOpenedApp = target.Replace(".exe", "").Replace(".EXE", "");
                            Debug.WriteLine($"[EXECUTOR] Tracking last app: {_lastOpenedApp}");
                            
                            // Verify app window is actually focused and ready for input
                            await VerifyAppReadyForInput(_lastOpenedApp);
                        }
                        else if (step.TryGetProperty("fallback_url", out var fallbackEl) && fallbackEl.ValueKind == JsonValueKind.String)
                        {
                            var fallbackUrl = fallbackEl.GetString() ?? "";
                            if (!string.IsNullOrWhiteSpace(fallbackUrl))
                            {
                                Debug.WriteLine($"[EXECUTOR] App open failed, falling back to web: {fallbackUrl}");
                                _automation.PressKey("enter");
                                _automation.PressKey("escape");
                                if (_automation.OpenApplication("chrome.exe"))
                                {
                                    await Task.Delay(800);
                                    _automation.Hotkey("ctrl+l");
                                    await Task.Delay(120);
                                    _automation.TypeIntoApp(fallbackUrl);
                                    _automation.PressKey("enter");
                                    result.Success = true;
                                    result.Details = "Fallback to web";
                                }
                            }
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

                // ===== SYSTEM TOGGLES (Quick Settings) =====
                case "toggle_quick_setting":
                    {
                        string settingName = step.TryGetProperty("target", out var snEl) ? (snEl.GetString() ?? "") : "";
                        string desired = step.TryGetProperty("state", out var stEl) ? (stEl.GetString() ?? "") : "";
                        desired = desired.Trim().ToLowerInvariant();

                        if (string.IsNullOrWhiteSpace(settingName))
                        {
                            result.Success = false;
                            result.Error = "Missing target for toggle_quick_setting";
                            break;
                        }

                        // Open Quick Settings
                        _automation.Hotkey("win+a");
                        await Task.Delay(600);

                        // Find the toggle button
                        var toggle = _uiFinder.FindButton(settingName);
                        if (toggle == null)
                        {
                            // Some builds expose these as non-Button elements; try generic search
                            toggle = _uiFinder.FindElement(settingName);
                        }

                        if (toggle == null)
                        {
                            result.Success = false;
                            result.Error = $"Quick Setting not found: {settingName}";
                            _automation.PressKey("esc");
                            break;
                        }

                        // If we can read toggle state and have a desired state, enforce it
                        var before = _uiFinder.GetToggleState(toggle);
                        bool hasDesired = desired == "on" || desired == "off";

                        if (hasDesired && before.HasValue)
                        {
                            bool isOn = before.Value == ToggleState.On;
                            bool wantOn = desired == "on";
                            if (isOn == wantOn)
                            {
                                result.Success = true;
                                _automation.PressKey("esc");
                                break;
                            }
                        }

                        // Toggle
                        result.Success = _uiFinder.ClickElement(toggle);
                        await Task.Delay(500);

                        if (result.Success && hasDesired)
                        {
                            var after = _uiFinder.GetToggleState(toggle);
                            if (after.HasValue)
                            {
                                bool isOnAfter = after.Value == ToggleState.On;
                                bool wantOnAfter = desired == "on";
                                if (isOnAfter != wantOnAfter)
                                {
                                    result.Success = false;
                                    result.Error = $"Toggle did not reach desired state: {desired}";
                                }
                            }
                        }

                        _automation.PressKey("esc");
                        break;
                    }

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
                        else if (IsVisionAllowed())
                        {
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
                                // Vision recovery: ask for a corrective action, execute it,
                                // then retry vision targeting once.
                                Debug.WriteLine($"[EXECUTOR] Vision targeting failed, attempting recovery for: '{description}'");

                                if (!string.IsNullOrEmpty(_currentGoal))
                                {
                                    var recoveryResult = await _visionRecovery.AttemptRecoveryAsync(
                                        _currentGoal,
                                        "click_element",
                                        $"Element not found: {description}"
                                    );

                                    if (recoveryResult.Success && recoveryResult.RecoveryAction != null)
                                    {
                                        var recoveryExec = await ExecuteRecoveryAction(recoveryResult.RecoveryAction);
                                        if (recoveryExec.Success)
                                        {
                                            await Task.Delay(400);
                                            var retry = await _visionRecovery.FindClickTargetAsync(description, _currentGoal);
                                            if (retry != null && retry.Success && retry.X > 0 && retry.Y > 0)
                                            {
                                                Debug.WriteLine($"[EXECUTOR] Vision retry found target at ({retry.X}, {retry.Y})");
                                                _automation.Click(retry.X, retry.Y);
                                                result.Success = true;
                                                result.Details = $"Vision click after recovery at ({retry.X}, {retry.Y}): {retry.Element}";
                                                break;
                                            }
                                        }
                                    }
                                }

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
                
                // Vision analysis (OpenCV-powered UI analysis)
                case "vision_analyze":
                    {
                        string analysisType = "comprehensive";
                        if (step.TryGetProperty("target", out var targetVar))
                        {
                            analysisType = targetVar.GetString() ?? "comprehensive";
                        }
                        
                        string content = "";
                        if (step.TryGetProperty("content", out var contentVar))
                        {
                            content = contentVar.GetString() ?? "";
                        }
                        
                        Debug.WriteLine($"[EXECUTOR] Vision analysis: {analysisType} for '{content}'");
                        
                        try
                        {
                            // Capture screenshot as base64
                            var screenshotPath = _automation.TakeScreenshot();
                            if (string.IsNullOrEmpty(screenshotPath))
                            {
                                result.Error = "Failed to capture screenshot";
                                break;
                            }
                            
                            // Convert screenshot to base64 with proper disposal
                            string base64Image;
                            using (var bitmap = new System.Drawing.Bitmap(screenshotPath))
                            using (var ms = new System.IO.MemoryStream())
                            {
                                bitmap.Save(ms, System.Drawing.Imaging.ImageFormat.Png);
                                base64Image = Convert.ToBase64String(ms.ToArray());
                            }
                            
                            // Clean up screenshot file
                            try { System.IO.File.Delete(screenshotPath); } catch { }
                            
                            // Call OpenCV vision API with proper HttpClient disposal
                            using var client = new HttpClient();
                            client.Timeout = TimeSpan.FromSeconds(10); // Add timeout
                            
                            var requestBody = new
                            {
                                image_b64 = base64Image,
                                target_description = content,
                                analysis_type = analysisType
                            };
                            
                            var json = JsonSerializer.Serialize(requestBody);
                            using var httpContent = new StringContent(json, Encoding.UTF8, "application/json");
                            
                            var response = await client.PostAsync("http://localhost:8000/api/agent/vision/analyze", httpContent);
                            
                            if (response.IsSuccessStatusCode)
                            {
                                var responseJson = await response.Content.ReadAsStringAsync();
                                Debug.WriteLine($"[EXECUTOR] Vision API response: {responseJson}");
                                
                                // Parse and surface results to user
                                using var doc = JsonDocument.Parse(responseJson);
                                var root = doc.RootElement;
                                
                                Debug.WriteLine($"[EXECUTOR] Response root properties: {string.Join(", ", root.EnumerateObject().Select(p => p.Name))}");
                                
                                if (root.TryGetProperty("buttons", out var buttonsEl) && buttonsEl.ValueKind == JsonValueKind.Array)
                                {
                                    var buttonsCount = buttonsEl.GetArrayLength();
                                    result.Success = true;
                                    result.Details = $"Found {buttonsCount} buttons on screen";
                                    Debug.WriteLine($"[EXECUTOR] SUCCESS: Found {buttonsCount} buttons");
                                    
                                    // Log button details
                                    for (int i = 0; i < Math.Min(buttonsCount, 5); i++)
                                    {
                                        var button = buttonsEl[i];
                                        if (button.TryGetProperty("x", out var xPos) && button.TryGetProperty("y", out var yPos))
                                        {
                                            Debug.WriteLine($"[EXECUTOR] Button {i+1}: ({xPos.GetInt32()}, {yPos.GetInt32()})");
                                        }
                                    }
                                }
                                else if (root.TryGetProperty("summary", out var summaryEl))
                                {
                                    result.Success = true;
                                    result.Details = summaryEl.GetString() ?? "Analysis complete";
                                    Debug.WriteLine($"[EXECUTOR] SUCCESS: {result.Details}");
                                }
                                else
                                {
                                    result.Success = true;
                                    result.Details = $"Vision analysis returned: {responseJson.Substring(0, Math.Min(200, responseJson.Length))}...";
                                    Debug.WriteLine($"[EXECUTOR] FALLBACK: {result.Details}");
                                }
                            }
                            else
                            {
                                var errorContent = await response.Content.ReadAsStringAsync();
                                result.Error = $"Vision API error: {response.StatusCode} - {errorContent}";
                                Debug.WriteLine($"[EXECUTOR] ERROR: {result.Error}");
                            }
                        }
                        catch (HttpRequestException ex)
                        {
                            result.Error = $"Vision API network error: {ex.Message}";
                            Debug.WriteLine($"[EXECUTOR] NETWORK ERROR: {ex.Message}");
                        }
                        catch (TaskCanceledException ex)
                        {
                            result.Error = $"Vision API timeout: {ex.Message}";
                            Debug.WriteLine($"[EXECUTOR] TIMEOUT ERROR: {ex.Message}");
                        }
                        catch (Exception ex)
                        {
                            result.Error = $"Vision analysis failed: {ex.Message}";
                            Debug.WriteLine($"[EXECUTOR] GENERAL ERROR: {ex.Message}");
                        }
                    }
                    break;
                
                // ===== FILE OPERATIONS =====
                case "create_file":
                    if (step.TryGetProperty("path", out var pathEl) && 
                        step.TryGetProperty("content", out var fileContentEl))
                    {
                        string filePath = pathEl.GetString() ?? "";
                        string fileContent = fileContentEl.GetString() ?? "";
                        result.Success = AdvancedActions.CreateFile(filePath, fileContent);
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

                // ===== PROCESS CONTROL =====
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

                // ===== CLIPBOARD =====
                case "copy_to_clipboard":
                    if (step.TryGetProperty("content", out var clipContentEl))
                    {
                        string clipContent = clipContentEl.GetString() ?? "";
                        result.Success = AdvancedActions.CopyToClipboard(clipContent);
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

                // ===== BEAST-LEVEL KEYBOARD CONTROL =====
                case "type_fast":
                    if (step.TryGetProperty("text", out var typeTextEl))
                    {
                        string typeText = typeTextEl.GetString() ?? "";
                        int delayMs = step.TryGetProperty("delay_ms", out var delayEl) ? 
                            delayEl.GetInt32() : 10;
                        result.Success = PowerfulExecutor.TypeFast(typeText, delayMs);
                    }
                    break;


                case "hold_key":
                    if (step.TryGetProperty("key", out var holdKeyEl) && 
                        step.TryGetProperty("duration_ms", out var durationEl))
                    {
                        string holdKey = holdKeyEl.GetString() ?? "";
                        int duration = durationEl.GetInt32();
                        result.Success = PowerfulExecutor.HoldKey(holdKey, duration);
                    }
                    break;


                // ===== BEAST-LEVEL MOUSE CONTROL =====

                case "click_mouse":
                    int clickX = step.TryGetProperty("x", out var clickXEl) ? clickXEl.GetInt32() : -1;
                    int clickY = step.TryGetProperty("y", out var clickYEl) ? clickYEl.GetInt32() : -1;
                    string clickButton = step.TryGetProperty("button", out var btnEl) ? 
                        (btnEl.GetString() ?? "left") : "left";
                    result.Success = PowerfulExecutor.ClickMouse(clickX, clickY, clickButton);
                    break;


                // ===== WINDOW CONTROL =====


                case "close_window":
                    if (step.TryGetProperty("process_name", out var closeProcEl))
                    {
                        string closeProc = closeProcEl.GetString() ?? "";
                        result.Success = PowerfulExecutor.CloseWindow(closeProc);
                    }
                    break;

                // ===== REGISTRY & SYSTEM CONFIG =====
                case "get_registry":
                    if (step.TryGetProperty("path", out var regPathEl) && 
                        step.TryGetProperty("value", out var regValEl))
                    {
                        string regPath = regPathEl.GetString() ?? "";
                        string regVal = regValEl.GetString() ?? "";
                        string regResult = PowerfulExecutor.GetRegistryValue(regPath, regVal);
                        result.Success = !string.IsNullOrEmpty(regResult);
                        result.Details = regResult;
                    }
                    break;

                case "set_registry":
                    if (step.TryGetProperty("path", out var setRegPathEl) && 
                        step.TryGetProperty("value", out var setRegValEl) &&
                        step.TryGetProperty("data", out var setDataEl))
                    {
                        string setRegPath = setRegPathEl.GetString() ?? "";
                        string setRegVal = setRegValEl.GetString() ?? "";
                        string setData = setDataEl.GetString() ?? "";
                        result.Success = PowerfulExecutor.SetRegistryValue(setRegPath, setRegVal, setData);
                    }
                    break;

                // ===== WEB AUTOMATION =====
                case "fetch_web":
                    if (step.TryGetProperty("url", out var fetchUrlEl))
                    {
                        string url = fetchUrlEl.GetString() ?? "";
                        var webTask = PowerfulExecutor.FetchWebPage(url);
                        webTask.Wait(10000);
                        string webContent = webTask.Result;
                        result.Success = !string.IsNullOrEmpty(webContent);
                        result.Details = webContent;
                    }
                    break;

                case "send_web_request":
                    if (step.TryGetProperty("url", out var reqUrlEl))
                    {
                        string reqUrl = reqUrlEl.GetString() ?? "";
                        string reqMethod = step.TryGetProperty("method", out var methodEl) ? 
                            (methodEl.GetString() ?? "GET") : "GET";
                        string reqBody = step.TryGetProperty("body", out var bodyEl) ? 
                            (bodyEl.GetString() ?? null) : null;
                        var webReqTask = PowerfulExecutor.SendWebRequest(reqUrl, reqMethod, reqBody);
                        webReqTask.Wait(10000);
                        result.Success = webReqTask.Result;
                    }
                    break;

                // ===== ENVIRONMENT & SYSTEM =====
                case "get_env_var":
                    if (step.TryGetProperty("name", out var envNameEl))
                    {
                        string envName = envNameEl.GetString() ?? "";
                        string envValue = PowerfulExecutor.GetEnvVariable(envName);
                        result.Success = !string.IsNullOrEmpty(envValue);
                        result.Details = envValue;
                    }
                    break;

                case "set_env_var":
                    if (step.TryGetProperty("name", out var setEnvNameEl) && 
                        step.TryGetProperty("value", out var setEnvValEl))
                    {
                        string setEnvName = setEnvNameEl.GetString() ?? "";
                        string setEnvVal = setEnvValEl.GetString() ?? "";
                        result.Success = PowerfulExecutor.SetEnvVariable(setEnvName, setEnvVal);
                    }
                    break;

                case "run_command":
                    if (step.TryGetProperty("command", out var cmdEl))
                    {
                        string cmd = cmdEl.GetString() ?? "";
                        string cmdArgs = step.TryGetProperty("args", out var argsEl) ? 
                            (argsEl.GetString() ?? "") : "";
                        var cmdTask = PowerfulExecutor.RunCommand(cmd, cmdArgs);
                        cmdTask.Wait(10000);
                        result.Success = !string.IsNullOrEmpty(cmdTask.Result);
                        result.Details = cmdTask.Result;
                    }
                    break;

                case "system_info":
                    string sysInfo = PowerfulExecutor.GetSystemInfo();
                    result.Success = !string.IsNullOrEmpty(sysInfo);
                    result.Details = sysInfo;
                    break;

                // ===== EXTENDED CLIPBOARD =====
                case "get_clipboard":
                    string clipboardText = PowerfulExecutor.GetClipboardText();
                    result.Success = !string.IsNullOrEmpty(clipboardText);
                    result.Details = clipboardText;
                    break;

                case "set_clipboard":
                    if (step.TryGetProperty("text", out var clipTextEl))
                    {
                        string clipText = clipTextEl.GetString() ?? "";
                        result.Success = PowerfulExecutor.SetClipboardText(clipText);
                    }
                    break;

                // ===== NOTIFICATIONS =====
                case "show_notification":
                    string notifTitle = step.TryGetProperty("title", out var titleEl) ? 
                        (titleEl.GetString() ?? "Kernel") : "Kernel";
                    string notifMsg = step.TryGetProperty("message", out var msgEl) ? 
                        (msgEl.GetString() ?? "") : "";
                    result.Success = PowerfulExecutor.ShowNotification(notifTitle, notifMsg);
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
        /// Uses adaptive polling for critical actions instead of fixed delays.
        /// </summary>
        private async Task GetInterActionDelay(string action)
        {
            switch (action)
            {
                case "open_app":
                    // App opening: wait with adaptive polling
                    await AdaptiveDelayWithPolling(1500, 5000, () => IsSystemReady());
                    break;
                    
                case "navigate":
                case "search":
                case "search_web":
                    // Navigation: wait for browser to settle
                    await AdaptiveDelayWithPolling(1000, 3000, () => IsSystemReady());
                    break;
                    
                case "type_text":
                    await Task.Delay(200);  // Small fixed delay after typing
                    break;
                    
                case "click":
                    
                default:
                    await Task.Delay(BASE_DELAY_MS);
                    break;
            }
        }

        /// <summary>
        /// Adaptive delay with polling - waits minimum time, then polls for readiness up to max time.
        /// </summary>
        private async Task AdaptiveDelayWithPolling(int minDelayMs, int maxDelayMs, Func<bool> readinessCheck)
        {
            await Task.Delay(minDelayMs);
            
            var stopwatch = Stopwatch.StartNew();
            while (stopwatch.ElapsedMilliseconds < (maxDelayMs - minDelayMs))
            {
                if (readinessCheck())
                {
                    Debug.WriteLine($"[EXECUTOR] System ready after {stopwatch.ElapsedMilliseconds + minDelayMs}ms");
                    return;
                }
                await Task.Delay(100);
            }
            
            Debug.WriteLine($"[EXECUTOR] Max delay reached: {maxDelayMs}ms");
        }

        /// <summary>
        /// Check if system is ready for next action (CPU not busy, windows stable).
        /// </summary>
        private bool IsSystemReady()
        {
            try
            {
                // Simple heuristic: check if active window title is stable
                var currentTitle = _context.ActiveWindowTitle;
                return !string.IsNullOrEmpty(currentTitle);
            }
            catch
            {
                return true; // Assume ready if check fails
            }
        }

        /// <summary>
        /// Verify app window is focused and ready for input.
        /// </summary>
        private async Task VerifyAppReadyForInput(string processName)
        {
            int attempts = 0;
            const int maxAttempts = 10;
            
            while (attempts < maxAttempts)
            {
                try
                {
                    _context.RefreshContext();
                    var activeProcess = _context.ActiveProcessName;
                    
                    if (activeProcess.Contains(processName, StringComparison.OrdinalIgnoreCase))
                    {
                        Debug.WriteLine($"[EXECUTOR] App '{processName}' is focused and ready");
                        await Task.Delay(200); // Extra safety buffer
                        return;
                    }
                    
                    Debug.WriteLine($"[EXECUTOR] Waiting for '{processName}' to be focused (attempt {attempts + 1}/{maxAttempts})");
                }
                catch
                {
                }
                
                attempts++;
                await Task.Delay(300);
            }
            
            Debug.WriteLine($"[EXECUTOR] Warning: Could not verify '{processName}' is focused, proceeding anyway");
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
            bool lastResult = true,
            string? sessionId = null)
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
                    session_id = sessionId,
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
                var bounds = System.Windows.Forms.Screen.PrimaryScreen?.Bounds ?? Rectangle.Empty;
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
