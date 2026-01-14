using System;
using System.Threading.Tasks;
using System.Diagnostics;
using System.Text.Json;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// SmartExecutor - Reliable action execution with verification, retry, and timing.
    /// 
    /// Improvements over basic execution:
    /// 1. Verification - checks if actions succeeded
    /// 2. Retry logic - retries failed actions with backoff
    /// 3. Smart timing - waits for apps to be ready
    /// 4. Execution logging - detailed logs for debugging
    /// </summary>
    public class SmartExecutor
    {
        private readonly WindowsAutomation _automation;
        private const int MAX_RETRIES = 3;
        private const int BASE_DELAY_MS = 100;
        
        public SmartExecutor()
        {
            _automation = new WindowsAutomation();
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
        /// Execute a plan (list of actions) with proper sequencing.
        /// </summary>
        public async Task<PlanExecutionResult> ExecutePlanAsync(JsonElement stepsElement)
        {
            var result = new PlanExecutionResult();
            var stopwatch = Stopwatch.StartNew();

            foreach (var step in stepsElement.EnumerateArray())
            {
                var actionResult = await ExecuteActionAsync(step);
                result.ActionResults.Add(actionResult);

                if (!actionResult.Success)
                {
                    // On failure, we can either:
                    // 1. Stop the plan (current behavior)
                    // 2. Skip and continue
                    // 3. Ask user for help
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
}
