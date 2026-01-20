using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Windowing;
using WinRT.Interop;
using System;
using dotenv.net;
using NAudio.Wave;
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
        private bool _isRecording = false;
        private string _loginDeviceId = Guid.NewGuid().ToString();
        private FirestoreRealtimeListener? _firestoreListener;
        
        // Python-based speech recognition service
        private SpeechService? _speechService;
        
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
            
            if (_speechService != null)
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
            // OPTIMIZED: Poll every 500ms for up to 2 minutes (faster response)
            var maxAttempts = 240; // 2 minutes * 60 seconds / 0.5 second intervals
            var attempt = 0;

            System.Diagnostics.Debug.WriteLine($"[AUTH] Starting FAST polling for deviceId: {_loginDeviceId}");

            while (attempt < maxAttempts)
            {
                await Task.Delay(500);  // FAST: 500ms instead of 2000ms
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
                System.Diagnostics.Debug.WriteLine("[SPEECH] Initializing Python-based speech recognition...");
                
                // Create SpeechService that uses Python API for transcription
                _speechService = new SpeechService();
                
                // Hook up events
                _speechService.OnTranscriptionReceived += (text) =>
                {
                    this.DispatcherQueue.TryEnqueue(async () =>
                    {
                        CommandInput.Text = text;
                        AddToThoughtLog($"[Voice] 🎤 \"{text}\"");
                        
                        // Auto-execute the command
                        if (!string.IsNullOrWhiteSpace(text))
                        {
                            await ExecuteAgentCommand(text);
                        }
                    });
                };
                
                _speechService.OnError += (error) =>
                {
                    this.DispatcherQueue.TryEnqueue(() =>
                    {
                        AddToThoughtLog($"[Voice] ⚠️ {error}");
                    });
                };
                
                _speechService.OnAudioLevel += (level) =>
                {
                    if (level > 0.01f)
                    {
                        _lastSpeechTime = DateTime.Now;
                    }
                };
                
                System.Diagnostics.Debug.WriteLine("[SPEECH] ✓ Python speech recognition initialized!");
                
                this.DispatcherQueue.TryEnqueue(() =>
                {
                    AddToThoughtLog("[Voice] ✓ Speech recognition ready (Python API)");
                });
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SPEECH] ❌ Init failed: {ex.Message}");
                
                this.DispatcherQueue.TryEnqueue(() =>
                {
                    AddToThoughtLog($"[Voice] ⚠️ Speech init failed: {ex.Message}");
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
                
                if (_speechService == null)
                {
                    AddToThoughtLog("[Voice] ⚠️ Speech not initialized. Trying to reinitialize...");
                    InitializeSpeechClient();
                    
                    if (_speechService == null)
                    {
                        AddToThoughtLog("[Voice] ❌ Could not initialize speech recognition.");
                        return;
                    }
                }

                // Reset state
                _currentTranscript = "";
                _lastSpeechTime = DateTime.Now;
                
                // Start recording with new SpeechService
                _speechService.StartRecording();
                _isRecording = true;
                
                // Visual feedback - turn button red when recording
                InternalMonologueVoiceButton.Background = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, 220, 53, 69)); // Red
                CommandInput.PlaceholderText = "🎤 Recording... Click mic to stop and transcribe";
                AddToThoughtLog("[Voice] 🎤 Recording - Speak your command, then click mic to stop");
                
                System.Diagnostics.Debug.WriteLine("[VOICE] Recording started");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE] Error starting: {ex.Message}");
                AddToThoughtLog($"[Voice] Error: {ex.Message}");
                _isRecording = false;
            }
        }

        /// <summary>
        /// Stops listening and sends audio to Python for transcription.
        /// </summary>
        private async void StopVoiceListening()
        {
            if (!_isRecording || _speechService == null) return;
            
            _isRecording = false;
            
            // Update UI immediately
            InternalMonologueVoiceButton.Background = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(0, 0, 0, 0));
            CommandInput.PlaceholderText = "Transcribing...";
            
            try
            {
                // Stop recording and send to Python for transcription
                AddToThoughtLog("[Voice] 📤 Sending audio to Python for transcription...");
                var transcription = await _speechService.StopAndTranscribeAsync();
                
                if (!string.IsNullOrWhiteSpace(transcription))
                {
                    CommandInput.Text = transcription;
                    AddToThoughtLog($"[Voice] 🎤 \"{transcription}\"");
                    
                    // Execute the command
                    await ExecuteAgentCommand(transcription);
                }
                else
                {
                    AddToThoughtLog("[Voice] ⚠️ Could not transcribe audio");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE] Transcription error: {ex.Message}");
                AddToThoughtLog($"[Voice] Error: {ex.Message}");
            }
            
            CommandInput.PlaceholderText = "Command Agent...";
            AddToThoughtLog("[Voice] 🛑 Recording stopped");
            System.Diagnostics.Debug.WriteLine("[VOICE] Recording stopped");
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

        #region Step Progress UI

        /// <summary>
        /// Show the step progress panel and initialize for a new execution.
        /// </summary>
        public void ShowStepProgress(int totalSteps, string initialStep = "Starting...")
        {
            DispatcherQueue.TryEnqueue(() =>
            {
                if (StepProgressPanel != null)
                {
                    StepProgressPanel.Visibility = Visibility.Visible;
                    StepCountText.Text = $"1/{totalSteps}";
                    CurrentStepText.Text = initialStep;
                    StepProgressBar.Width = 0;
                    StepProgressTitle.Text = "EXECUTING PLAN";
                }
            });
        }

        /// <summary>
        /// Update the step progress display.
        /// </summary>
        public void UpdateStepProgress(int currentStep, int totalSteps, string action, string status = "running")
        {
            DispatcherQueue.TryEnqueue(() =>
            {
                if (StepProgressPanel != null)
                {
                    StepCountText.Text = $"{currentStep}/{totalSteps}";
                    
                    // Format action name for display
                    string displayAction = FormatActionName(action);
                    CurrentStepText.Text = status == "success" 
                        ? $"✓ {displayAction}" 
                        : $"{displayAction}...";
                    
                    // Update progress bar (assuming StepProgressBar parent width ~240)
                    double progress = (double)currentStep / totalSteps;
                    StepProgressBar.Width = progress * 240;
                    
                    // Update title based on status
                    if (status == "success" && currentStep == totalSteps)
                    {
                        StepProgressTitle.Text = "✓ COMPLETE";
                        StepProgressTitle.Foreground = new Microsoft.UI.Xaml.Media.SolidColorBrush(
                            Microsoft.UI.Colors.LimeGreen);
                    }
                    else if (status == "failed")
                    {
                        StepProgressTitle.Text = "✗ FAILED";
                        StepProgressTitle.Foreground = new Microsoft.UI.Xaml.Media.SolidColorBrush(
                            Microsoft.UI.Colors.Tomato);
                    }
                }
            });
        }

        /// <summary>
        /// Hide the step progress panel after execution.
        /// </summary>
        public void HideStepProgress(int delayMs = 2000)
        {
            Task.Run(async () =>
            {
                await Task.Delay(delayMs);
                DispatcherQueue.TryEnqueue(() =>
                {
                    if (StepProgressPanel != null)
                    {
                        StepProgressPanel.Visibility = Visibility.Collapsed;
                        // Reset title color
                        StepProgressTitle.Foreground = new Microsoft.UI.Xaml.Media.SolidColorBrush(
                            Windows.UI.Color.FromArgb(255, 142, 117, 255)); // #8E75FF
                        StepProgressTitle.Text = "EXECUTING PLAN";
                    }
                });
            });
        }

        /// <summary>
        /// Execute a voice or text command through the agent API.
        /// </summary>
        private async Task ExecuteAgentCommand(string command)
        {
            try
            {
                AddToThoughtLog($"[Agent] Executing: {command}");
                await ApiService.Instance.SendCommandAsync(command);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AGENT] Command error: {ex.Message}");
                AddToThoughtLog($"[Agent] Error: {ex.Message}");
            }
        }

        /// <summary>
        /// Format action name for user-friendly display.
        /// </summary>
        private string FormatActionName(string action)
        {
            return action switch
            {
                "open_app" => "Opening application",
                "navigate" => "Navigating to page",
                "type_text" => "Typing text",
                "click" => "Clicking",
                "click_element" => "Finding and clicking",
                "wait" => "Waiting",
                "smart_wait" => "Waiting for ready",
                "press_key" => "Pressing key",
                "hotkey" => "Sending hotkey",
                "scroll" => "Scrolling",
                "search" => "Searching",
                _ => action.Replace("_", " ")
            };
        }

        #endregion
    }
}