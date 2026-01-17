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
using System.Speech.Recognition;  // Windows built-in speech

namespace Kernel_Agent
{
    public sealed partial class MainWindow : Window
    {
        private OrbOverlayWindow? _orbOverlayWindow;
        private bool _isRecording = false;
        private string _loginDeviceId = Guid.NewGuid().ToString();
        private FirestoreRealtimeListener? _firestoreListener;
        
        // Windows built-in speech recognition (no API key needed!)
        private SpeechRecognitionEngine? _speechRecognizer;
        
        // Voice recording state
        private string _currentTranscript = "";
        private DateTime _lastSpeechTime = DateTime.Now;
        private System.Timers.Timer? _silenceTimer;
        private const int SILENCE_THRESHOLD_MS = 2000; // 2 seconds of silence = auto-send

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

        private void StartContinuousVoiceListening()
        {
            // Just initialize the Windows speech recognizer - it's set up to use button-triggered recording
            System.Diagnostics.Debug.WriteLine("[UI] *** Initializing Windows speech recognition...");
            InitializeSpeechClient();
            
            if (_speechRecognizer != null)
            {
                AddToThoughtLog("🎤 [Voice] Ready! Click the microphone button to speak.");
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

        private void InitializeSpeechClient()
        {
            try
            {
                System.Diagnostics.Debug.WriteLine("[SPEECH] Initializing Windows Speech Recognition...");
                
                // Use Windows built-in speech recognition with ENHANCED settings
                _speechRecognizer = new SpeechRecognitionEngine(
                    System.Globalization.CultureInfo.CurrentCulture);
                
                // === ACCURACY IMPROVEMENTS ===
                
                // 1. Load dictation grammar with enhancements
                var dictationGrammar = new DictationGrammar("grammar:dictation");
                dictationGrammar.Name = "Dictation";
                _speechRecognizer.LoadGrammar(dictationGrammar);
                
                // 2. Add custom grammar for common PC commands (more accurate than dictation alone)
                var commandChoices = new Choices(
                    // App control
                    "open", "close", "launch", "start", "run",
                    "notepad", "chrome", "word", "excel", "spotify", "discord", "teams", "outlook",
                    "browser", "file explorer", "settings", "calculator", "paint",
                    // Actions
                    "type", "write", "search", "google", "find",
                    "copy", "paste", "cut", "undo", "redo", "save", "select all",
                    // Media
                    "play", "pause", "stop", "next", "previous", "volume up", "volume down", "mute",
                    // Window
                    "minimize", "maximize", "close window", "alt tab", "switch window",
                    // Navigation
                    "scroll up", "scroll down", "go back", "go forward", "refresh",
                    // YouTube shortcuts
                    "skip ad", "fullscreen", "next video",
                    // Desktop
                    "next desktop", "previous desktop", "new desktop", "task view",
                    // Common words
                    "and", "then", "the", "a", "to", "in", "on", "for", "with",
                    "hello", "hi", "hey", "please", "thank you"
                );
                
                var commandBuilder = new GrammarBuilder(commandChoices);
                commandBuilder.Culture = System.Globalization.CultureInfo.CurrentCulture;
                var commandGrammar = new Grammar(commandBuilder);
                commandGrammar.Name = "Commands";
                _speechRecognizer.LoadGrammar(commandGrammar);
                
                // 3. Configure audio input for better quality
                _speechRecognizer.SetInputToDefaultAudioDevice();
                
                // 4. Tune recognition settings for accuracy
                _speechRecognizer.InitialSilenceTimeout = TimeSpan.FromSeconds(5);    // Wait 5sec for user to start speaking
                _speechRecognizer.BabbleTimeout = TimeSpan.FromSeconds(3);             // Keep listening during pauses
                _speechRecognizer.EndSilenceTimeout = TimeSpan.FromSeconds(1.5);       // 1.5sec silence = end of speech
                _speechRecognizer.EndSilenceTimeoutAmbiguous = TimeSpan.FromSeconds(2); // 2sec for ambiguous endings
                
                // 5. Event handlers
                _speechRecognizer.SpeechRecognized += SpeechRecognizer_SpeechRecognized;
                _speechRecognizer.SpeechHypothesized += SpeechRecognizer_SpeechHypothesized;
                _speechRecognizer.SpeechRecognitionRejected += SpeechRecognizer_SpeechRejected;
                _speechRecognizer.AudioLevelUpdated += SpeechRecognizer_AudioLevelUpdated;
                
                System.Diagnostics.Debug.WriteLine("[SPEECH] ✓ Windows Speech Recognition initialized with enhanced accuracy!");
                
                this.DispatcherQueue.TryEnqueue(() =>
                {
                    AddToThoughtLog("[Voice] ✓ Speech recognition ready (enhanced accuracy)");
                });
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SPEECH] ❌ Init failed: {ex.Message}");
                
                this.DispatcherQueue.TryEnqueue(() =>
                {
                    AddToThoughtLog($"[Voice] ⚠️ Speech init failed: {ex.Message}");
                    AddToThoughtLog("[Voice] Try: Control Panel → Speech Recognition → Train");
                });
            }
        }

        private void SpeechRecognizer_AudioLevelUpdated(object? sender, AudioLevelUpdatedEventArgs e)
        {
            // Update visual feedback based on audio level (optional)
            if (e.AudioLevel > 0 && _isRecording)
            {
                _lastSpeechTime = DateTime.Now; // Reset silence timer when hearing audio
            }
        }

        private void SpeechRecognizer_SpeechHypothesized(object? sender, SpeechHypothesizedEventArgs e)
        {
            // Show interim results while user is still speaking
            _lastSpeechTime = DateTime.Now;
            
            System.Diagnostics.Debug.WriteLine($"[SPEECH] Hypothesis: {e.Result.Text}");
            
            this.DispatcherQueue.TryEnqueue(() =>
            {
                CommandInput.Text = e.Result.Text + "...";
            });
        }

        private void SpeechRecognizer_SpeechRecognized(object? sender, SpeechRecognizedEventArgs e)
        {
            // Accept with lower confidence threshold since we have custom grammar
            if (e.Result.Confidence > 0.1 || e.Result.Grammar?.Name == "Commands")
            {
                _currentTranscript = e.Result.Text;
                _lastSpeechTime = DateTime.Now;
                
                System.Diagnostics.Debug.WriteLine($"[SPEECH] ✓ Recognized: \"{e.Result.Text}\" (Confidence: {e.Result.Confidence:P0}, Grammar: {e.Result.Grammar?.Name})");
                
                this.DispatcherQueue.TryEnqueue(() =>
                {
                    CommandInput.Text = e.Result.Text;
                });
            }
            else
            {
                System.Diagnostics.Debug.WriteLine($"[SPEECH] Rejected low confidence: {e.Result.Confidence:P0}");
            }
        }

        private void SpeechRecognizer_SpeechRejected(object? sender, SpeechRecognitionRejectedEventArgs e)
        {
            System.Diagnostics.Debug.WriteLine($"[SPEECH] Not understood. Best guess: \"{e.Result.Text}\" (Confidence: {e.Result.Confidence:P0})");
            
            // If the rejected result has some confidence, still use it
            if (e.Result.Confidence > 0.05 && !string.IsNullOrWhiteSpace(e.Result.Text))
            {
                _currentTranscript = e.Result.Text;
                _lastSpeechTime = DateTime.Now;
                
                this.DispatcherQueue.TryEnqueue(() =>
                {
                    CommandInput.Text = e.Result.Text + " (?)";
                });
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

        #region Voice Intelligence (Continuous Mode)

        private void VoiceInputButton_Click(object sender, RoutedEventArgs e)
        {
            if (!_isRecording) StartVoiceInput();
            else StopVoiceListening();  // Only button click stops listening
        }

        private void StartVoiceInput()
        {
            try
            {
                if (_isRecording) return;
                
                if (_speechRecognizer == null)
                {
                    AddToThoughtLog("[Voice] ⚠️ Speech not initialized. Trying to reinitialize...");
                    InitializeSpeechClient();
                    
                    if (_speechRecognizer == null)
                    {
                        AddToThoughtLog("[Voice] ❌ Could not initialize speech recognition.");
                        return;
                    }
                }

                // Reset state
                _currentTranscript = "";
                _lastSpeechTime = DateTime.Now;
                
                // Start recognition asynchronously in CONTINUOUS mode
                _speechRecognizer.RecognizeAsync(RecognizeMode.Multiple);
                _isRecording = true;
                
                // Visual feedback - turn button red when recording
                InternalMonologueVoiceButton.Background = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, 220, 53, 69)); // Red
                CommandInput.PlaceholderText = "🎤 Continuous mode - Click mic to stop";
                AddToThoughtLog("[Voice] 🎤 CONTINUOUS MODE - Say commands, pause to execute, click mic to stop");
                
                // Start silence detection timer for auto-execute (but NOT auto-stop)
                _silenceTimer?.Stop();
                _silenceTimer = new System.Timers.Timer(500); // Check every 500ms
                _silenceTimer.Elapsed += CheckForSilenceAndExecute;
                _silenceTimer.Start();
                
                System.Diagnostics.Debug.WriteLine("[VOICE] Continuous mode started");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE] Error starting: {ex.Message}");
                AddToThoughtLog($"[Voice] Error: {ex.Message}");
                _isRecording = false;
            }
        }

        private void CheckForSilenceAndExecute(object? sender, System.Timers.ElapsedEventArgs e)
        {
            if (!_isRecording) return;
            
            var silenceDuration = (DateTime.Now - _lastSpeechTime).TotalMilliseconds;
            
            // If we have text and silence exceeded threshold, execute but KEEP LISTENING
            if (!string.IsNullOrWhiteSpace(_currentTranscript) && silenceDuration >= SILENCE_THRESHOLD_MS)
            {
                string commandToExecute = _currentTranscript;
                _currentTranscript = ""; // Clear so we don't execute again
                
                System.Diagnostics.Debug.WriteLine($"[VOICE] Pause detected - executing: {commandToExecute}");
                
                this.DispatcherQueue.TryEnqueue(async () =>
                {
                    // Execute the command
                    AddToThoughtLog($"[Voice] 📤 Executing: \"{commandToExecute}\"");
                    CommandInput.Text = "";
                    await ApiService.Instance.SendCommandAsync(commandToExecute);
                    
                    // Show that we're still listening
                    CommandInput.PlaceholderText = "🎤 Listening for next command...";
                    AddToThoughtLog("[Voice] ✓ Done. Say another command or click mic to stop");
                });
                
                // Reset speech time to prevent re-execution
                _lastSpeechTime = DateTime.Now;
            }
        }

        /// <summary>
        /// Stops listening completely (only called when user clicks the button)
        /// </summary>
        private void StopVoiceListening()
        {
            _silenceTimer?.Stop();
            _silenceTimer?.Dispose();
            _silenceTimer = null;
            
            // Stop recognition
            try
            {
                _speechRecognizer?.RecognizeAsyncStop();
            }
            catch { }
            
            _isRecording = false;
            
            // Reset button color
            InternalMonologueVoiceButton.Background = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(0, 0, 0, 0));
            CommandInput.PlaceholderText = "Command Agent...";
            
            // If there's pending text, execute it
            if (!string.IsNullOrWhiteSpace(_currentTranscript))
            {
                string finalCommand = _currentTranscript;
                _currentTranscript = "";
                
                this.DispatcherQueue.TryEnqueue(async () =>
                {
                    AddToThoughtLog($"[Voice] 📤 Final command: \"{finalCommand}\"");
                    CommandInput.Text = "";
                    await ApiService.Instance.SendCommandAsync(finalCommand);
                });
            }
            
            AddToThoughtLog("[Voice] 🛑 Continuous mode stopped");
            System.Diagnostics.Debug.WriteLine("[VOICE] Continuous mode stopped");
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