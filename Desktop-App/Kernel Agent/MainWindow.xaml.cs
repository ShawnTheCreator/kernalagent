using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Windowing;
using WinRT.Interop;
using System;
using dotenv.net;
using NAudio.Wave;
using Google.Cloud.Speech.V1;
using System.Threading.Tasks;
using System.IO;
using System.Collections.Generic;
using Kernel_Agent.Services;
using Microsoft.UI.Xaml.Input;

namespace Kernel_Agent
{
    public sealed partial class MainWindow : Window
    {
        private OrbOverlayWindow? _orbOverlayWindow;
        private WaveInEvent? _waveIn;
        private SpeechClient _speechClient;
        private bool _isRecording = false;
        private string _loginDeviceId = Guid.NewGuid().ToString();
        private FirestoreRealtimeListener? _firestoreListener;
        
        // Continuous voice service for always-listening mode
        private ContinuousVoiceService? _voiceService;
        
        // Voice recording state
        private string _currentTranscript = "";
        private DateTime _lastSpeechTime = DateTime.Now;
        private System.Timers.Timer? _silenceTimer;
        private const int SILENCE_THRESHOLD_MS = 1500; // 1.5 seconds of silence = auto-send

        public MainWindow()
        {
            InitializeComponent();
            // WinUI 3: Use AppWindow.Changed event for minimize/restore
            var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);
            var appWindow = Microsoft.UI.Windowing.AppWindow.GetFromWindowId(
                Microsoft.UI.Win32Interop.GetWindowIdFromWindow(hwnd)
            );
            appWindow.Changed += AppWindow_Changed;

            try
            {
                DotEnv.Load();

                // Modern Title Bar Extension
                ExtendsContentIntoTitleBar = true;
                SetTitleBar(AppTitleBar);

                // Default UI State
                if (MissionRoot != null && ContentFrame != null)
                {
                    MissionRoot.Visibility = Visibility.Visible;
                    ContentFrame.Visibility = Visibility.Collapsed;
                }

                // Start spinner animation
                StartSpinnerAnimation();

                // Check authentication on startup
                CheckAuthenticationAsync();

                // Initialize Speech Client Once (Preventing the MoveNext error source)
                InitializeSpeechClient();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Critical Init Error: {ex.Message}");
            }
        }

        private void StartSpinnerAnimation()
        {
            var storyboard = new Microsoft.UI.Xaml.Media.Animation.Storyboard();
            var animation = new Microsoft.UI.Xaml.Media.Animation.DoubleAnimation
            {
                From = 0,
                To = 360,
                Duration = new Duration(TimeSpan.FromSeconds(1)),
                RepeatBehavior = Microsoft.UI.Xaml.Media.Animation.RepeatBehavior.Forever
            };
            Microsoft.UI.Xaml.Media.Animation.Storyboard.SetTarget(animation, SpinnerRotation);
            Microsoft.UI.Xaml.Media.Animation.Storyboard.SetTargetProperty(animation, "Angle");
            storyboard.Children.Add(animation);
            storyboard.Begin();
        }

        private async void CheckAuthenticationAsync()
        {
            // Wait a moment for the window to be fully loaded
            await Task.Delay(100);
            
            var isAuthenticated = await ApiService.Instance.IsAuthenticatedAsync();
            if (isAuthenticated)
            {
                // User is already logged in, show profile
                await ShowUserProfileAsync();
            }
            else
            {
                // Show login UI
                ShowLoginButton();
                
                // Automatically open browser to login (Windsurf style)
                await OpenWebLoginAsync();
            }
        }

        private void ShowLoginButton()
        {
            // Show the separate login overlay
            if (LoginOverlay != null) LoginOverlay.Visibility = Visibility.Visible;
            if (NavView != null) NavView.Visibility = Visibility.Collapsed;
            
            // Header login button can be hidden or shown. Let's hide it to focus on the big screen.
            if (LoginButton != null) LoginButton.Visibility = Visibility.Collapsed; 
            if (ProfileSection != null) ProfileSection.Visibility = Visibility.Collapsed;
        }

        private void ShowProfileSection()
        {
            if (LoginButton != null) LoginButton.Visibility = Visibility.Collapsed;
            if (ProfileSection != null) ProfileSection.Visibility = Visibility.Visible;
            
            // Show main app content
            if (LoginOverlay != null) LoginOverlay.Visibility = Visibility.Collapsed;
            if (NavView != null) NavView.Visibility = Visibility.Visible;
        }

        private async Task ShowUserProfileAsync()
        {
            System.Diagnostics.Debug.WriteLine("[UI] ShowUserProfileAsync called");
            
            try
            {
                var user = await ApiService.Instance.GetCurrentUserAsync();
                
                this.DispatcherQueue.TryEnqueue(() =>
                {
                    if (user != null)
                    {
                        System.Diagnostics.Debug.WriteLine($"[UI] User loaded: {user.Name}");
                        UserNameText.Text = user.Name;
                        // Set profile picture if available
                        if (!string.IsNullOrEmpty(user.Email))
                        {
                            ProfilePicture.DisplayName = user.Name;
                            ProfilePicture.Initials = user.Name.Length >= 2 ? user.Name.Substring(0, 2).ToUpper() : "U";
                        }
                    }
                    else
                    {
                        System.Diagnostics.Debug.WriteLine("[UI] User is null, using default name");
                        UserNameText.Text = "User";
                        ProfilePicture.Initials = "U";
                    }
                    
                    // Always show profile section after successful login
                    System.Diagnostics.Debug.WriteLine("[UI] Showing profile section");
                    ShowProfileSection();

                    // Start Listening to Firestore "Brain" - wrapped in try-catch to prevent credential errors
                    try
                    {
                        var projectId = Environment.GetEnvironmentVariable("GOOGLE_CLOUD_PROJECT") ?? "kernel-agent-brain";
                        var credentialsPath = Environment.GetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS");
                        
                        // Only create listener if credentials are configured
                        if (!string.IsNullOrEmpty(credentialsPath) && System.IO.File.Exists(credentialsPath) && _firestoreListener == null)
                        {
                            var sessionId = user?.Id.ToString() ?? "default";
                            _firestoreListener = new FirestoreRealtimeListener(projectId, sessionId, OnMonologueUpdate);
                            System.Diagnostics.Debug.WriteLine("[UI] Firestore listener started");
                        }
                        else
                        {
                            System.Diagnostics.Debug.WriteLine("[UI] Firestore listener skipped - credentials not configured");
                        }
                    }
                    catch (Exception fsEx)
                    {
                        System.Diagnostics.Debug.WriteLine($"[UI] Firestore listener failed: {fsEx.Message}");
                        // Don't crash the app - continue without real-time updates
                    }
                    
                    // Start continuous voice listening
                    StartContinuousVoiceListening();
                });
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[UI] Error loading user profile: {ex.Message}");
                
                // Even if we can't load user details, still show the main interface
                this.DispatcherQueue.TryEnqueue(() =>
                {
                    System.Diagnostics.Debug.WriteLine("[UI] Showing profile section despite error");
                    UserNameText.Text = "User";
                    ProfilePicture.Initials = "U";
                    ShowProfileSection();
                });
            }
        }

        private void OnMonologueUpdate(string thought)
        {
            if (string.IsNullOrEmpty(thought)) return;

            this.DispatcherQueue.TryEnqueue(() =>
            {
                // Add new thought to the log
                var textBlock = new TextBlock
                {
                    Text = $"> {thought}",
                    Foreground = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, 0, 255, 0)), // Terminal Green
                    TextWrapping = TextWrapping.Wrap,
                    Margin = new Thickness(0, 0, 0, 4),
                    FontFamily = new Microsoft.UI.Xaml.Media.FontFamily("Consolas")
                };
                ThoughtLog.Children.Add(textBlock);
                
                // Auto-scroll to bottom (if ScrollViewer is accessible, or just let users scroll)
                // If ThoughtLog is in a ScrollViewer, it would be nice to scroll to end.
            });
        }

        private async void StartContinuousVoiceListening()
        {
            try
            {
                System.Diagnostics.Debug.WriteLine("[UI] *** Initializing continuous voice service...");
                AddToThoughtLog("[Voice] Initializing...");
                
                _voiceService = new ContinuousVoiceService();
                
                // Subscribe to events for UI updates
                _voiceService.OnStatusChanged += (status) =>
                {
                    System.Diagnostics.Debug.WriteLine($"[VOICE-EVENT] Status: {status}");
                    this.DispatcherQueue.TryEnqueue(() =>
                    {
                        AddToThoughtLog($"[Voice] {status}");
                    });
                };
                
                _voiceService.OnSpeechRecognized += (text) =>
                {
                    System.Diagnostics.Debug.WriteLine($"[VOICE-EVENT] Recognized: {text}");
                    this.DispatcherQueue.TryEnqueue(() =>
                    {
                        AddToThoughtLog($"🎤 You said: \"{text}\"", true);
                    });
                };
                
                _voiceService.OnCommandExecuted += (command) =>
                {
                    System.Diagnostics.Debug.WriteLine($"[VOICE-EVENT] Executed: {command}");
                    this.DispatcherQueue.TryEnqueue(() =>
                    {
                        AddToThoughtLog($"✓ Executed: {command}");
                    });
                };
                
                // Connect voice states to orb visual feedback
                _voiceService.OnVoiceStateChanged += (state) =>
                {
                    System.Diagnostics.Debug.WriteLine($"[VOICE-EVENT] State: {state}");
                    this.DispatcherQueue.TryEnqueue(() =>
                    {
                        if (_orbOverlayWindow != null)
                        {
                            switch (state)
                            {
                                case VoiceState.Idle:
                                    _orbOverlayWindow.StartIdleAnimation();
                                    break;
                                case VoiceState.Listening:
                                    _orbOverlayWindow.SetListening();
                                    break;
                                case VoiceState.Processing:
                                    _orbOverlayWindow.SetProcessing();
                                    break;
                                case VoiceState.Speaking:
                                    _orbOverlayWindow.SetSpeaking();
                                    break;
                                case VoiceState.Success:
                                    _orbOverlayWindow.ShowSuccess();
                                    break;
                            }
                        }
                    });
                };
                
                // Initialize and start listening
                System.Diagnostics.Debug.WriteLine("[UI] *** Calling InitializeAsync...");
                await _voiceService.InitializeAsync();
                System.Diagnostics.Debug.WriteLine("[UI] *** InitializeAsync complete!");
                
                _voiceService.StartListening();
                
                System.Diagnostics.Debug.WriteLine("[UI] *** Continuous voice listening started!");
                AddToThoughtLog("🎤 [Voice] Listening! Speak naturally.");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[UI] *** Voice service FAILED: {ex.Message}");
                System.Diagnostics.Debug.WriteLine($"[UI] *** Stack: {ex.StackTrace}");
                AddToThoughtLog($"❌ [Voice] Error: {ex.Message}");
            }
        }

        private async void CommandInput_KeyDown(object sender, KeyRoutedEventArgs e)
        {
            if (e.Key == Windows.System.VirtualKey.Enter)
            {
                var text = CommandInput.Text;
                if (!string.IsNullOrWhiteSpace(text))
                {
                    CommandInput.Text = ""; // Clear input
                    AddToThoughtLog($"User: {text}", true);
                    await ApiService.Instance.SendCommandAsync(text);
                }
            }
        }

        private void AddToThoughtLog(string message, bool isUser = false)
        {
             var textBlock = new TextBlock
            {
                Text = message,
                Foreground = isUser ? 
                    new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, 255, 255, 255)) : 
                    new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, 0, 255, 0)),
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 4),
                FontFamily = new Microsoft.UI.Xaml.Media.FontFamily("Consolas")
            };
            ThoughtLog.Children.Add(textBlock);
        }

        private async void LoginButton_Click(object sender, RoutedEventArgs e)
        {
            await OpenWebLoginAsync();
        }

        private async Task OpenWebLoginAsync()
        {
            try
            {
                // Show loading overlay
                if (LoginLoadingOverlay != null)
                {
                    LoginLoadingOverlay.Visibility = Visibility.Visible;
                }

                // Open browser for web login
                var webAppUrl = Environment.GetEnvironmentVariable("WEB_APP_URL") ?? "https://kernalagent.vercel.app";
                var loginUrl = $"{webAppUrl}/login?deviceId={_loginDeviceId}";
                await Windows.System.Launcher.LaunchUriAsync(new Uri(loginUrl));
                
                // Update status
                if (LoadingStatusText != null)
                {
                    LoadingStatusText.Text = "Browser opened. Please login...";
                }

                // Start polling for authentication status
                await PollAuthenticationStatusAsync();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error opening web login: {ex.Message}");
                // Hide loading on error
                if (LoginLoadingOverlay != null)
                {
                    LoginLoadingOverlay.Visibility = Visibility.Collapsed;
                }
            }
        }

        private async Task PollAuthenticationStatusAsync()
        {
            // Poll every 2 seconds for up to 5 minutes
            var maxAttempts = 150; // 5 minutes * 60 seconds / 2 second intervals
            var attempt = 0;

            System.Diagnostics.Debug.WriteLine($"[AUTH] Starting polling for deviceId: {_loginDeviceId}");

            while (attempt < maxAttempts)
            {
                await Task.Delay(2000);
                attempt++;

                System.Diagnostics.Debug.WriteLine($"[AUTH] Poll attempt {attempt}/{maxAttempts}");

                // Update UI with polling status
                this.DispatcherQueue.TryEnqueue(() =>
                {
                    if (LoadingStatusText != null)
                    {
                        LoadingStatusText.Text = $"Checking for login... ({attempt})";
                    }
                });

                // Check backend for token using deviceId
                var success = await ApiService.Instance.CheckLoginStatusAsync(_loginDeviceId);
                
                System.Diagnostics.Debug.WriteLine($"[AUTH] Poll result: {success}");
                
                if (success)
                {
                    System.Diagnostics.Debug.WriteLine("[AUTH] Login detected! Switching to main interface...");
                    
                    // IMMEDIATELY switch to main interface on UI thread
                    this.DispatcherQueue.TryEnqueue(() =>
                    {
                        System.Diagnostics.Debug.WriteLine("[AUTH] Hiding loading overlay and login screen...");
                        
                        // Hide loading overlay
                        if (LoginLoadingOverlay != null)
                        {
                            LoginLoadingOverlay.Visibility = Visibility.Collapsed;
                        }
                        
                        // Hide login overlay, show main navigation
                        if (LoginOverlay != null) 
                        {
                            LoginOverlay.Visibility = Visibility.Collapsed;
                            System.Diagnostics.Debug.WriteLine("[AUTH] LoginOverlay hidden");
                        }
                        if (NavView != null) 
                        {
                            NavView.Visibility = Visibility.Visible;
                            System.Diagnostics.Debug.WriteLine("[AUTH] NavView shown");
                        }
                        
                        // Set default user info
                        if (UserNameText != null) UserNameText.Text = "User";
                        if (ProfilePicture != null) ProfilePicture.Initials = "U";
                        if (LoginButton != null) LoginButton.Visibility = Visibility.Collapsed;
                        if (ProfileSection != null) ProfileSection.Visibility = Visibility.Visible;
                        
                        System.Diagnostics.Debug.WriteLine("[AUTH] Main interface activated!");
                    });
                    
                    // Load user details in background (non-blocking)
                    _ = Task.Run(async () => {
                        try
                        {
                            var user = await ApiService.Instance.GetCurrentUserAsync();
                            if (user != null)
                            {
                                this.DispatcherQueue.TryEnqueue(() =>
                                {
                                    UserNameText.Text = user.Name;
                                    ProfilePicture.DisplayName = user.Name;
                                    ProfilePicture.Initials = user.Name.Length >= 2 ? user.Name.Substring(0, 2).ToUpper() : "U";
                                });
                            }
                        }
                        catch (Exception ex)
                        {
                            System.Diagnostics.Debug.WriteLine($"[AUTH] Background user load failed: {ex.Message}");
                        }
                    });
                    
                    break;
                }
            }

            if (attempt >= maxAttempts)
            {
                System.Diagnostics.Debug.WriteLine("[AUTH] Polling timeout reached");
                
                // Hide loading overlay
                this.DispatcherQueue.TryEnqueue(() =>
                {
                    if (LoginLoadingOverlay != null)
                    {
                        LoginLoadingOverlay.Visibility = Visibility.Collapsed;
                    }
                });

                // Timeout - show error message
                await ShowAuthenticationTimeoutDialog();
            }
        }

        private async Task ShowAuthenticationTimeoutDialog()
        {
            // Ensure we have a valid root for the dialog
            if (ContentFrame == null || ContentFrame.XamlRoot == null) return;

            var dialog = new ContentDialog
            {
                Title = "Login Timeout",
                Content = "Login session timed out. Please try again.",
                CloseButtonText = "OK",
                XamlRoot = ContentFrame.XamlRoot
            };
            await dialog.ShowAsync();
        }

        private async void LogoutMenuItem_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                await ApiService.Instance.LogoutAsync();
                ShowLoginButton();
                
                // Clear profile picture
                ProfilePicture.DisplayName = string.Empty;
                ProfilePicture.Initials = string.Empty;
                UserNameText.Text = string.Empty;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Logout error: {ex.Message}");
            }
        }

        // Removed the old ShowLoginDialogAsync and ShowSignupDialogAsync as we are using Web Login now exclusively per user request.

        private async void InitializeSpeechClient()
        {
            try
            {
                // Create the client once to be reused across all audio chunks
                _speechClient = await SpeechClient.CreateAsync();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Speech Client Init Failed: {ex.Message}");
            }
        }

        #region Navigation Logic

        private void NavView_SelectionChanged(NavigationView sender, NavigationViewSelectionChangedEventArgs args)
        {
            if (args.IsSettingsSelected)
            {
                NavigateToPage(typeof(SettingsPage));
            }
            else
            {
                var selectedItem = args.SelectedItem as NavigationViewItem;
                if (selectedItem?.Tag == null) return;

                string tag = selectedItem.Tag.ToString();
                switch (tag)
                {
                    case "mission":
                        ContentFrame.Visibility = Visibility.Collapsed;
                        MissionRoot.Visibility = Visibility.Visible;
                        break;
                    case "forge":
                        NavigateToPage(typeof(ForgePage));
                        break;
                    case "memory":
                        NavigateToPage(typeof(MemoryPage));
                        break;
                    case "history":
                        NavigateToPage(typeof(HistoryPage));
                        break;
                    case "security":
                        NavigateToPage(typeof(SecurityPage));
                        break;
                    case "sandbox":
                        NavigateToPage(typeof(SandboxPage));
                        break;
                    case "marketplace":
                        NavigateToPage(typeof(MarketplacePage));
                        break;
                }
            }
        }

        private void NavigateToPage(Type pageType)
        {
            if (MissionRoot == null || ContentFrame == null) return;

            MissionRoot.Visibility = Visibility.Collapsed;
            ContentFrame.Visibility = Visibility.Visible;

            if (ContentFrame.Content?.GetType() != pageType)
            {
                ContentFrame.Navigate(pageType);
            }
        }

        #endregion

        #region Voice Intelligence (Fixed Logic)

        // Audio buffer for collecting speech
        private List<byte> _audioBuffer = new List<byte>();
        private SpeechClient.StreamingRecognizeStream? _streamingCall;
        private Task? _responseTask;

        private void VoiceInputButton_Click(object sender, RoutedEventArgs e)
        {
            if (!_isRecording) StartVoiceInput();
            else StopVoiceInputAndSend();
        }

        private async void StartVoiceInput()
        {
            try
            {
                if (_isRecording) return;
                if (_speechClient == null)
                {
                    AddToThoughtLog("[Voice] ⚠️ Speech client not initialized. Check Google credentials.");
                    return;
                }

                // Reset state
                _currentTranscript = "";
                _audioBuffer.Clear();
                _lastSpeechTime = DateTime.Now;
                
                // Dispose any existing instance
                _waveIn?.Dispose();
                _waveIn = null;

                _waveIn = new WaveInEvent
                {
                    WaveFormat = new WaveFormat(16000, 1), // 16kHz Mono for Speech
                    BufferMilliseconds = 100
                };
                
                _waveIn.DataAvailable += OnAudioDataAvailable;
                _waveIn.StartRecording();
                _isRecording = true;
                
                // Visual feedback - turn button red when recording
                InternalMonologueVoiceButton.Background = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, 220, 53, 69)); // Red
                CommandInput.PlaceholderText = "🎤 Listening... Speak now!";
                AddToThoughtLog("[Voice] 🎤 Recording started - speak now!");
                
                // Start silence detection timer
                _silenceTimer?.Stop();
                _silenceTimer = new System.Timers.Timer(500); // Check every 500ms
                _silenceTimer.Elapsed += CheckForSilence;
                _silenceTimer.Start();
                
                // Start streaming recognition
                await StartStreamingRecognition();
                
                System.Diagnostics.Debug.WriteLine("Voice Recording Started.");
            }
            catch (NAudio.MmException ex)
            {
                HandleMicrophoneError(ex.Message);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Voice recording error: {ex.Message}");
                AddToThoughtLog($"[Voice] Error: {ex.Message}");
                _isRecording = false;
                _waveIn?.Dispose();
                _waveIn = null;
            }
        }

        private async Task StartStreamingRecognition()
        {
            try
            {
                _streamingCall = _speechClient.StreamingRecognize();
                
                // Send configuration
                await _streamingCall.WriteAsync(new StreamingRecognizeRequest
                {
                    StreamingConfig = new StreamingRecognitionConfig
                    {
                        Config = new RecognitionConfig
                        {
                            Encoding = RecognitionConfig.Types.AudioEncoding.Linear16,
                            SampleRateHertz = 16000,
                            LanguageCode = "en-US",
                            EnableAutomaticPunctuation = true,
                        },
                        InterimResults = true,
                        SingleUtterance = false
                    }
                });
                
                // Start reading responses in background
                _responseTask = Task.Run(async () =>
                {
                    try
                    {
                        await foreach (var response in _streamingCall.GetResponseStream())
                        {
                            foreach (var result in response.Results)
                            {
                                if (result.Alternatives.Count > 0)
                                {
                                    string transcript = result.Alternatives[0].Transcript;
                                    bool isFinal = result.IsFinal;
                                    
                                    _lastSpeechTime = DateTime.Now; // Reset silence timer
                                    
                                    // Update UI on main thread
                                    this.DispatcherQueue.TryEnqueue(() =>
                                    {
                                        if (isFinal)
                                        {
                                            _currentTranscript = transcript;
                                            CommandInput.Text = transcript;
                                            System.Diagnostics.Debug.WriteLine($"[VOICE] Final: {transcript}");
                                        }
                                        else
                                        {
                                            CommandInput.Text = transcript + "...";
                                            System.Diagnostics.Debug.WriteLine($"[VOICE] Interim: {transcript}");
                                        }
                                    });
                                }
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        System.Diagnostics.Debug.WriteLine($"Response stream error: {ex.Message}");
                    }
                });
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Streaming init error: {ex.Message}");
            }
        }

        private async void OnAudioDataAvailable(object? sender, WaveInEventArgs e)
        {
            if (!_isRecording || _streamingCall == null || e.BytesRecorded == 0) return;

            try
            {
                // Send audio data to Google
                await _streamingCall.WriteAsync(new StreamingRecognizeRequest
                {
                    AudioContent = Google.Protobuf.ByteString.CopyFrom(e.Buffer, 0, e.BytesRecorded)
                });
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Audio send error: {ex.Message}");
            }
        }

        private void CheckForSilence(object? sender, System.Timers.ElapsedEventArgs e)
        {
            if (!_isRecording) return;
            
            var silenceDuration = (DateTime.Now - _lastSpeechTime).TotalMilliseconds;
            
            // If we have text and silence exceeded threshold, auto-send
            if (!string.IsNullOrWhiteSpace(_currentTranscript) && silenceDuration >= SILENCE_THRESHOLD_MS)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE] Silence detected ({silenceDuration}ms), auto-sending...");
                
                this.DispatcherQueue.TryEnqueue(() =>
                {
                    StopVoiceInputAndSend();
                });
            }
        }

        private async void StopVoiceInputAndSend()
        {
            _silenceTimer?.Stop();
            _silenceTimer?.Dispose();
            _silenceTimer = null;
            
            _waveIn?.StopRecording();
            _waveIn?.Dispose();
            _waveIn = null;
            _isRecording = false;
            
            // Close streaming call
            try
            {
                if (_streamingCall != null)
                {
                    await _streamingCall.WriteCompleteAsync();
                    _streamingCall = null;
                }
            }
            catch { }
            
            // Reset button color
            InternalMonologueVoiceButton.Background = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(0, 0, 0, 0));
            CommandInput.PlaceholderText = "Command Agent...";
            
            // Send the command if we have transcribed text
            string command = CommandInput.Text?.Trim() ?? "";
            if (!string.IsNullOrWhiteSpace(command) && !command.EndsWith("..."))
            {
                AddToThoughtLog($"[Voice] 📤 Sending: \"{command}\"");
                CommandInput.Text = "";
                await ApiService.Instance.SendCommandAsync(command);
            }
            else if (!string.IsNullOrWhiteSpace(_currentTranscript))
            {
                AddToThoughtLog($"[Voice] 📤 Sending: \"{_currentTranscript}\"");
                CommandInput.Text = "";
                await ApiService.Instance.SendCommandAsync(_currentTranscript);
            }
            else
            {
                AddToThoughtLog("[Voice] Recording stopped (no speech detected)");
            }
        }

        private void HandleMicrophoneError(string message)
        {
            System.Diagnostics.Debug.WriteLine($"Microphone access error: {message}");
            _isRecording = false;
            _waveIn?.Dispose();
            _waveIn = null;
            
            this.DispatcherQueue.TryEnqueue(async () =>
            {
                AddToThoughtLog($"[Voice] ⚠️ Microphone error: {message}");
                
                if (ContentFrame?.XamlRoot != null)
                {
                    var dialog = new ContentDialog
                    {
                        Title = "Microphone Access Error",
                        Content = "Unable to access microphone. Please check:\n1. Microphone permissions are enabled\n2. No other application is using the microphone\n3. A microphone is connected and working",
                        CloseButtonText = "OK",
                        XamlRoot = ContentFrame.XamlRoot
                    };
                    await dialog.ShowAsync();
                }
            });
        }

        #endregion

        private void AppWindow_Changed(Microsoft.UI.Windowing.AppWindow sender, object args)
        {
            if (sender.Presenter is Microsoft.UI.Windowing.OverlappedPresenter presenter)
            {
                if (presenter.State == Microsoft.UI.Windowing.OverlappedPresenterState.Minimized)
                {
                    // Create and show the floating orb overlay
                    if (_orbOverlayWindow == null)
                    {
                        _orbOverlayWindow = new OrbOverlayWindow();
                        
                        // Wire up orb events
                        _orbOverlayWindow.OnExpandRequested += () =>
                        {
                            // Restore main window
                            DispatcherQueue.TryEnqueue(() =>
                            {
                                this.Activate();
                                var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);
                                var windowId = Microsoft.UI.Win32Interop.GetWindowIdFromWindow(hwnd);
                                var appWindow = Microsoft.UI.Windowing.AppWindow.GetFromWindowId(windowId);
                                if (appWindow.Presenter is Microsoft.UI.Windowing.OverlappedPresenter p)
                                {
                                    p.Restore();
                                }
                            });
                        };
                        
                        _orbOverlayWindow.OnExitRequested += () =>
                        {
                            // Close entire application
                            DispatcherQueue.TryEnqueue(() =>
                            {
                                _orbOverlayWindow?.Close();
                                _orbOverlayWindow = null;
                                this.Close();
                            });
                        };
                    }
                    
                    try 
                    {
                        _orbOverlayWindow.Activate();
                    } 
                    catch (Exception ex) 
                    {
                        System.Diagnostics.Debug.WriteLine($"Error activating Orb: {ex.Message}");
                        // Re-create if disposed/closed unexpectedly
                        _orbOverlayWindow = new OrbOverlayWindow();
                        _orbOverlayWindow.Activate();
                    }
                }
                else
                {
                    _orbOverlayWindow?.Close();
                    _orbOverlayWindow = null;
                }
            }
        }
    }
}