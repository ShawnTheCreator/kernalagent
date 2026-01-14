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
        private readonly string _pythonBackendUrl = "http://localhost:8000/api/agent/plan"; // Change to your deployed Python backend if needed
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
            using var doc = JsonDocument.Parse(json);
            return doc.RootElement.EnumerateArray().Select(element => element).ToArray();
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
                    // ===== APP CONTROL =====
                    case "open_app":
                        bool success = _automation.OpenApplication(step.GetProperty("target").GetString() ?? "");
                        if (!success)
                        {
                            System.Diagnostics.Debug.WriteLine("[VOICE] Failed to open/verify app. Aborting plan.");
                            // Future: Take screenshot and ask user for help
                            return; 
                        }
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
                    
                    default:
                        System.Diagnostics.Debug.WriteLine($"[VOICE] Unknown action: {action}");
                        break;
                }
                
                await Task.Delay(100); // Small delay between actions
            }
        }
    }
}
