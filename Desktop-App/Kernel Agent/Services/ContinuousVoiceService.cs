using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Linq;
using System.Threading.Tasks;
using System.Threading;
using NAudio.Wave;
using Google.Cloud.Speech.V1;
using Google.Protobuf;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Voice states for visual feedback in the orb.
    /// </summary>
    public enum VoiceState
    {
        Idle,       // Calm breathing
        Listening,  // Blue pulse - listening for input
        Processing, // Spinner - recognizing/thinking
        Speaking,   // Glow expansion - agent responding
        Success     // Green flash - command completed
    }

    /// <summary>
    /// Enhanced voice service with:
    /// - Continuous background listening
    /// - Silence/pause detection to know when sentence ends
    /// - Google Cloud Speech API for accurate recognition
    /// - Voice state events for visual feedback
    /// - Works even when app is minimized
    /// </summary>
    public class ContinuousVoiceService : IDisposable
    {
        // Audio configuration
        private const int SAMPLE_RATE = 16000;
        private const int CHANNELS = 1;
        private const int SILENCE_THRESHOLD = 500;      // Amplitude threshold for silence
        private const int SILENCE_DURATION_MS = 1500;   // 1.5 seconds of silence = end of sentence
        private const int MIN_SPEECH_DURATION_MS = 500; // Minimum speech to process
        
        private readonly WindowsAutomation _automation = new WindowsAutomation();
        private readonly string _pythonBackendUrl = "http://localhost:8000/api/agent/plan/v2";
        
        private WaveInEvent? _waveIn;
        private SpeechClient? _speechClient;
        private bool _isListening = false;
        private bool _isDisposed = false;
        
        // Audio buffering for pause detection
        private readonly System.Collections.Generic.List<byte> _audioBuffer = new();
        private DateTime _lastSoundTime = DateTime.Now;
        private DateTime _speechStartTime = DateTime.Now;
        private bool _isSpeaking = false;
        private readonly object _bufferLock = new();
        
        // Events for UI feedback
        public event Action<string>? OnStatusChanged;
        public event Action<string>? OnSpeechRecognized;
        public event Action<string>? OnCommandExecuted;
        public event Action<bool>? OnListeningStateChanged;
        
        /// <summary>
        /// Fired when voice state changes - use for orb visual feedback.
        /// </summary>
        public event Action<VoiceState>? OnVoiceStateChanged;

        public bool IsListening => _isListening;

        public async Task InitializeAsync()
        {
            try
            {
                _speechClient = await SpeechClient.CreateAsync();
                System.Diagnostics.Debug.WriteLine("[VOICE] Google Cloud Speech client initialized");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE] Speech client init failed: {ex.Message}");
                throw;
            }
        }

        public void StartListening()
        {
            if (_isListening || _isDisposed) return;

            try
            {
                _waveIn = new WaveInEvent
                {
                    WaveFormat = new WaveFormat(SAMPLE_RATE, 16, CHANNELS),
                    BufferMilliseconds = 100
                };
                
                _waveIn.DataAvailable += OnAudioDataAvailable;
                _waveIn.RecordingStopped += OnRecordingStopped;
                _waveIn.StartRecording();
                
                _isListening = true;
                _lastSoundTime = DateTime.Now;
                
                OnStatusChanged?.Invoke("Listening...");
                OnListeningStateChanged?.Invoke(true);
                OnVoiceStateChanged?.Invoke(VoiceState.Listening);
                
                System.Diagnostics.Debug.WriteLine("[VOICE] Started continuous listening");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE] Failed to start: {ex.Message}");
                OnStatusChanged?.Invoke($"Error: {ex.Message}");
            }
        }

        public void StopListening()
        {
            if (!_isListening) return;

            try
            {
                _waveIn?.StopRecording();
                _waveIn?.Dispose();
                _waveIn = null;
                
                _isListening = false;
                OnStatusChanged?.Invoke("Stopped");
                OnListeningStateChanged?.Invoke(false);
                
                System.Diagnostics.Debug.WriteLine("[VOICE] Stopped listening");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE] Stop error: {ex.Message}");
            }
        }

        private void OnAudioDataAvailable(object? sender, WaveInEventArgs e)
        {
            if (!_isListening || e.BytesRecorded == 0) return;

            // Calculate audio level (RMS)
            int sum = 0;
            for (int i = 0; i < e.BytesRecorded; i += 2)
            {
                short sample = BitConverter.ToInt16(e.Buffer, i);
                sum += Math.Abs(sample);
            }
            int avgLevel = sum / (e.BytesRecorded / 2);

            bool isSoundDetected = avgLevel > SILENCE_THRESHOLD;

            lock (_bufferLock)
            {
                if (isSoundDetected)
                {
                    if (!_isSpeaking)
                    {
                        // Speech started
                        _isSpeaking = true;
                        _speechStartTime = DateTime.Now;
                        _audioBuffer.Clear();
                        OnStatusChanged?.Invoke("Listening... (speaking detected)");
                        System.Diagnostics.Debug.WriteLine("[VOICE] Speech started");
                    }
                    
                    _lastSoundTime = DateTime.Now;
                    
                    // Add audio to buffer
                    byte[] chunk = new byte[e.BytesRecorded];
                    Array.Copy(e.Buffer, chunk, e.BytesRecorded);
                    _audioBuffer.AddRange(chunk);
                }
                else if (_isSpeaking)
                {
                    // Add audio even during brief pauses
                    byte[] chunk = new byte[e.BytesRecorded];
                    Array.Copy(e.Buffer, chunk, e.BytesRecorded);
                    _audioBuffer.AddRange(chunk);
                    
                    // Check if silence duration exceeded (end of sentence)
                    var silenceDuration = (DateTime.Now - _lastSoundTime).TotalMilliseconds;
                    var speechDuration = (DateTime.Now - _speechStartTime).TotalMilliseconds;
                    
                    if (silenceDuration >= SILENCE_DURATION_MS && speechDuration >= MIN_SPEECH_DURATION_MS)
                    {
                        // End of sentence detected - process the audio
                        _isSpeaking = false;
                        
                        byte[] audioData = _audioBuffer.ToArray();
                        _audioBuffer.Clear();
                        
                        OnStatusChanged?.Invoke("Processing...");
                        System.Diagnostics.Debug.WriteLine($"[VOICE] Sentence complete ({speechDuration:F0}ms speech, {audioData.Length} bytes)");
                        
                        // Process in background
                        _ = ProcessAudioAsync(audioData);
                    }
                }
            }
        }

        private async Task ProcessAudioAsync(byte[] audioData)
        {
            if (_speechClient == null || audioData.Length < 1000) return;

            try
            {
                // Signal processing state
                OnVoiceStateChanged?.Invoke(VoiceState.Processing);
                
                // Send to Google Cloud Speech
                var response = await _speechClient.RecognizeAsync(new RecognitionConfig
                {
                    Encoding = RecognitionConfig.Types.AudioEncoding.Linear16,
                    SampleRateHertz = SAMPLE_RATE,
                    LanguageCode = "en-US",
                    EnableAutomaticPunctuation = true,
                    Model = "command_and_search" // Optimized for short commands
                }, 
                RecognitionAudio.FromBytes(audioData));

                // Get best transcript
                string? transcript = response.Results
                    .Select(r => r.Alternatives.FirstOrDefault()?.Transcript)
                    .FirstOrDefault(t => !string.IsNullOrWhiteSpace(t));

                if (!string.IsNullOrWhiteSpace(transcript))
                {
                    System.Diagnostics.Debug.WriteLine($"[VOICE] Recognized: {transcript}");
                    OnSpeechRecognized?.Invoke(transcript);
                    OnStatusChanged?.Invoke($"Heard: \"{transcript}\"");
                    
                    // Signal speaking/executing state
                    OnVoiceStateChanged?.Invoke(VoiceState.Speaking);
                    
                    // Execute the command
                    await ExecuteCommandAsync(transcript);
                    
                    // Signal success
                    OnVoiceStateChanged?.Invoke(VoiceState.Success);
                }
                
                // Return to listening state
                OnStatusChanged?.Invoke("Listening...");
                OnVoiceStateChanged?.Invoke(VoiceState.Listening);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE] Recognition error: {ex.Message}");
                OnStatusChanged?.Invoke("Listening...");
                OnVoiceStateChanged?.Invoke(VoiceState.Listening);
            }
        }

        private async Task ExecuteCommandAsync(string command)
        {
            try
            {
                OnStatusChanged?.Invoke("Executing...");
                
                using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
                var requestBody = new { command };
                var content = new StringContent(JsonSerializer.Serialize(requestBody), Encoding.UTF8, "application/json");
                
                var response = await client.PostAsync(_pythonBackendUrl, content);
                
                if (!response.IsSuccessStatusCode)
                {
                    System.Diagnostics.Debug.WriteLine($"[VOICE] API error: {response.StatusCode}");
                    OnStatusChanged?.Invoke("Listening...");
                    return;
                }

                var json = await response.Content.ReadAsStringAsync();
                System.Diagnostics.Debug.WriteLine($"[VOICE] API Response: {json}");
                
                using var doc = JsonDocument.Parse(json);
                
                JsonElement[]? steps = null;
                if (doc.RootElement.TryGetProperty("steps", out var stepsElement))
                {
                    steps = stepsElement.EnumerateArray().Select(e => e.Clone()).ToArray();
                }
                
                if (steps != null && steps.Length > 0)
                {
                    await ExecuteActionPlan(steps);
                    OnCommandExecuted?.Invoke(command);
                }
                
                OnStatusChanged?.Invoke("Listening...");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE] Execute error: {ex.Message}");
                OnStatusChanged?.Invoke("Listening...");
            }
        }

        private async Task ExecuteActionPlan(JsonElement[] steps)
        {
            foreach (var step in steps)
            {
                if (!step.TryGetProperty("action", out var actionProp)) continue;
                string action = actionProp.GetString() ?? "";
                
                System.Diagnostics.Debug.WriteLine($"[VOICE] Executing: {action}");

                switch (action)
                {
                    case "open_app":
                        string target = step.TryGetProperty("target", out var t) ? t.GetString() ?? "" : "";
                        _automation.OpenApplication(target);
                        await Task.Delay(1500);
                        break;
                    case "close_app":
                        string closeTarget = step.TryGetProperty("target", out var ct) ? ct.GetString() ?? "" : "";
                        _automation.CloseApplication(closeTarget);
                        await Task.Delay(500);
                        break;
                    case "type_text":
                        string text = step.TryGetProperty("content", out var c) ? c.GetString() ?? "" : "";
                        _automation.TypeIntoApp(text);
                        break;
                    case "navigate":
                        string url = step.TryGetProperty("url", out var u) ? u.GetString() ?? "" : "";
                        _automation.TypeIntoApp(url + "\n");
                        await Task.Delay(1500);
                        break;
                    case "search":
                    case "search_web":
                        string query = step.TryGetProperty("query", out var q) ? q.GetString() ?? "" : "";
                        _automation.TypeIntoApp(query + "\n");
                        await Task.Delay(1500);
                        break;
                    case "volume_up":
                        int volUp = step.TryGetProperty("amount", out var vu) ? vu.GetInt32() : 1;
                        _automation.VolumeUp(volUp);
                        break;
                    case "volume_down":
                        int volDown = step.TryGetProperty("amount", out var vd) ? vd.GetInt32() : 1;
                        _automation.VolumeDown(volDown);
                        break;
                    case "volume_mute":
                        _automation.VolumeMute();
                        break;
                    case "minimize_window":
                        _automation.MinimizeWindow();
                        break;
                    case "maximize_window":
                        _automation.MaximizeWindow();
                        break;
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
                    case "save":
                        _automation.Save();
                        break;
                    case "alt_tab":
                        _automation.AltTab();
                        break;
                    case "show_desktop":
                        _automation.ShowDesktop();
                        break;
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
                    case "brightness_up":
                        int brUp = step.TryGetProperty("amount", out var bu) ? bu.GetInt32() : 10;
                        _automation.BrightnessUp(brUp);
                        break;
                    case "brightness_down":
                        int brDown = step.TryGetProperty("amount", out var bd) ? bd.GetInt32() : 10;
                        _automation.BrightnessDown(brDown);
                        break;
                    default:
                        System.Diagnostics.Debug.WriteLine($"[VOICE] Unknown action: {action}");
                        break;
                }

                await Task.Delay(100);
            }
        }

        private void OnRecordingStopped(object? sender, StoppedEventArgs e)
        {
            if (e.Exception != null)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE] Recording error: {e.Exception.Message}");
            }
        }

        public void Dispose()
        {
            if (_isDisposed) return;
            _isDisposed = true;
            
            StopListening();
            _speechClient = null;
        }
    }
}
