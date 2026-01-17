using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Linq;
using System.Threading.Tasks;
using System.Speech.Recognition;
using Kernel_Agent.Services;

namespace Kernel_Agent.Services
{
    public class VoiceToActionService
    {
        private readonly WindowsAutomation _automation = new WindowsAutomation();
        // Using LLM-First Architecture (v2) - intelligent multi-step command processing
        // Production: Render deployed backend
        private readonly string _pythonBackendUrl = "https://kernalagent.onrender.com/api/agent/plan/v2";
        private readonly SpeechRecognitionEngine _recognizer;

        public VoiceToActionService()
        {
            _recognizer = new SpeechRecognitionEngine();
            _recognizer.SetInputToDefaultAudioDevice();
            _recognizer.LoadGrammar(new DictationGrammar());
            _recognizer.SpeechRecognized += Recognizer_SpeechRecognized;
        }

        public void StartListening()
        {
            _recognizer.RecognizeAsync(RecognizeMode.Multiple);
        }

        public void StopListening()
        {
            _recognizer.RecognizeAsyncStop();
        }

        private async void Recognizer_SpeechRecognized(object sender, SpeechRecognizedEventArgs e)
        {
            string recognizedText = e.Result.Text;
            var actionPlan = await GetActionPlanFromPython(recognizedText);
            if (actionPlan != null)
            {
                await ExecuteActionPlan(actionPlan);
            }
        }

        private async Task<JsonElement[]> GetActionPlanFromPython(string userCommand)
        {
            using var client = new HttpClient();
            var requestBody = new { command = userCommand };
            var content = new StringContent(JsonSerializer.Serialize(requestBody), Encoding.UTF8, "application/json");
            var response = await client.PostAsync(_pythonBackendUrl, content);
            if (!response.IsSuccessStatusCode) return null;
            var json = await response.Content.ReadAsStringAsync();
            System.Diagnostics.Debug.WriteLine($"[VOICE] API Response: {json}");
            using var doc = JsonDocument.Parse(json);
            
            // The API returns {"session_id": "...", "steps": [...]}
            // We need to extract the "steps" array
            if (doc.RootElement.TryGetProperty("steps", out var stepsElement))
            {
                return stepsElement.EnumerateArray().Select(element => element.Clone()).ToArray();
            }
            
            // Fallback: try root as array (old format)
            if (doc.RootElement.ValueKind == JsonValueKind.Array)
            {
                return doc.RootElement.EnumerateArray().Select(element => element.Clone()).ToArray();
            }
            
            return null;
        }

        private async Task ExecuteActionPlan(JsonElement[] steps)
        {
            foreach (var step in steps)
            {
                string action = step.GetProperty("action").GetString() ?? "";
                System.Diagnostics.Debug.WriteLine($"[VOICE] Executing action: {action}");
                
                switch (action)
                {
                    // ===== APP CONTROL =====
                    case "open_app":
                        string appTarget = step.GetProperty("target").GetString() ?? "";
                        bool success = _automation.OpenApplication(appTarget);
                        if (!success)
                        {
                            System.Diagnostics.Debug.WriteLine("[VOICE] App may not be fully ready, continuing anyway...");
                        }
                        // Always wait for app to stabilize before next action
                        await Task.Delay(1500);
                        break;
                    case "close_app":
                        _automation.CloseApplication(step.GetProperty("target").GetString() ?? "");
                        await Task.Delay(500);
                        break;
                    
                    // ===== TEXT INPUT =====
                    case "type_text":
                        _automation.TypeIntoApp(step.GetProperty("content").GetString() ?? "");
                        break;
                    case "navigate":
                        _automation.TypeIntoApp((step.GetProperty("url").GetString() ?? "") + "\n");
                        await Task.Delay(1500);
                        break;
                    case "search":
                    case "search_web":
                        _automation.TypeIntoApp((step.GetProperty("query").GetString() ?? "") + "\n");
                        await Task.Delay(1500);
                        break;
                    
                    // ===== VOLUME =====
                    case "volume_up":
                        int volUp = step.TryGetProperty("amount", out var amtUp) ? amtUp.GetInt32() : 1;
                        _automation.VolumeUp(volUp);
                        break;
                    case "volume_down":
                        int volDown = step.TryGetProperty("amount", out var amtDown) ? amtDown.GetInt32() : 1;
                        _automation.VolumeDown(volDown);
                        break;
                    case "volume_mute":
                        _automation.VolumeMute();
                        break;
                    
                    // ===== WINDOW =====
                    case "minimize_window":
                        _automation.MinimizeWindow();
                        break;
                    case "maximize_window":
                        _automation.MaximizeWindow();
                        break;
                    case "restore_window":
                        _automation.RestoreWindow();
                        break;
                    
                    // ===== SYSTEM =====
                    case "lock_screen":
                        _automation.LockScreen();
                        break;
                    case "sleep":
                        _automation.Sleep();
                        break;
                    case "shutdown":
                        _automation.Shutdown();
                        break;
                    case "restart":
                        _automation.Restart();
                        break;
                    case "screenshot":
                        _automation.TakeScreenshot();
                        break;
                    
                    // ===== CLIPBOARD =====
                    case "copy":
                        _automation.Copy();
                        break;
                    case "paste":
                        _automation.Paste();
                        break;
                    case "cut":
                        _automation.Cut();
                        break;
                    case "undo":
                        _automation.Undo();
                        break;
                    case "redo":
                        _automation.Redo();
                        break;
                    case "select_all":
                        _automation.SelectAll();
                        break;
                    case "save":
                        _automation.Save();
                        break;
                    
                    // ===== WINDOW SWITCHING =====
                    case "alt_tab":
                        _automation.AltTab();
                        break;
                    case "show_desktop":
                        _automation.ShowDesktop();
                        break;
                    
                    // ===== KEYBOARD =====
                    case "press_key":
                        _automation.PressKey(step.GetProperty("content").GetString() ?? "");
                        break;
                    case "hotkey":
                        _automation.Hotkey(step.GetProperty("content").GetString() ?? "");
                        break;
                    
                    // ===== MEDIA =====
                    case "media_play_pause":
                        _automation.MediaPlayPause();
                        break;
                    case "media_next":
                        _automation.MediaNext();
                        break;
                    case "media_previous":
                        _automation.MediaPrevious();
                        break;
                    case "media_stop":
                        _automation.MediaStop();
                        break;
                    
                    // ===== BROWSER =====
                    case "new_tab":
                        _automation.NewTab();
                        break;
                    case "close_tab":
                        _automation.CloseTab();
                        break;
                    case "refresh":
                        _automation.Refresh();
                        break;
                    case "go_back":
                        _automation.GoBack();
                        break;
                    case "go_forward":
                        _automation.GoForward();
                        break;
                    
                    // ===== MOUSE =====
                    case "click":
                        if (step.TryGetProperty("x", out var xProp) && step.TryGetProperty("y", out var yProp))
                        {
                            _automation.Click(xProp.GetInt32(), yProp.GetInt32());
                        }
                        break;
                    case "double_click":
                        if (step.TryGetProperty("x", out var dxProp) && step.TryGetProperty("y", out var dyProp))
                        {
                            _automation.DoubleClick(dxProp.GetInt32(), dyProp.GetInt32());
                        }
                        break;
                    case "right_click":
                        if (step.TryGetProperty("x", out var rxProp) && step.TryGetProperty("y", out var ryProp))
                        {
                            _automation.RightClick(rxProp.GetInt32(), ryProp.GetInt32());
                        }
                        break;
                    case "move_mouse":
                        if (step.TryGetProperty("x", out var mxProp) && step.TryGetProperty("y", out var myProp))
                        {
                            _automation.MoveMouse(mxProp.GetInt32(), myProp.GetInt32());
                        }
                        break;
                    case "scroll":
                        string dir = step.TryGetProperty("target", out var dirProp) ? dirProp.GetString() ?? "down" : "down";
                        _automation.Scroll(dir);
                        break;
                    
                    // ===== BRIGHTNESS =====
                    case "brightness_up":
                        int brUp = step.TryGetProperty("amount", out var brUpAmt) ? brUpAmt.GetInt32() : 10;
                        _automation.BrightnessUp(brUp);
                        break;
                    case "brightness_down":
                        int brDown = step.TryGetProperty("amount", out var brDownAmt) ? brDownAmt.GetInt32() : 10;
                        _automation.BrightnessDown(brDown);
                        break;
                    
                    // ===== VIRTUAL DESKTOP =====
                    case "switch_desktop_left":
                    case "desktop_left":
                    case "previous_desktop":
                        _automation.SwitchDesktopLeft();
                        break;
                    case "switch_desktop_right":
                    case "desktop_right":
                    case "next_desktop":
                        _automation.SwitchDesktopRight();
                        break;
                    case "new_desktop":
                    case "create_desktop":
                        _automation.NewDesktop();
                        break;
                    case "close_desktop":
                        _automation.CloseDesktop();
                        break;
                    case "task_view":
                    case "show_desktops":
                        _automation.TaskView();
                        break;
                    
                    // ===== WAIT =====
                    case "wait":
                        int waitMs = step.TryGetProperty("duration", out var durEl) ? durEl.GetInt32() * 1000 : 2000;
                        await Task.Delay(waitMs);
                        break;
                    
                    // ===== YOUTUBE =====
                    case "youtube_skip_ad":
                        _automation.PressKey("tab");
                        await Task.Delay(100);
                        _automation.PressKey("enter");
                        break;
                    case "youtube_play":
                    case "youtube_pause":
                        _automation.PressKey("space");
                        break;
                    case "youtube_fullscreen":
                        _automation.Hotkey("f");
                        break;
                    case "youtube_next":
                        _automation.Hotkey("shift+n");
                        break;
                    
                    default:
                        System.Diagnostics.Debug.WriteLine($"[VOICE] Unknown action: {action}");
                        break;
                }
                
                await Task.Delay(100); // Small delay between actions
            }
        }
    }
}
