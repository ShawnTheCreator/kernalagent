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

namespace Kernel_Agent
{
    public sealed partial class MainWindow : Window
    {
        private WaveInEvent _waveIn;
        private SpeechClient _speechClient;
        private bool _isRecording = false;

        public MainWindow()
        {
            try
            {
                this.InitializeComponent();
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

        private async void CheckAuthenticationAsync()
        {
            var isAuthenticated = await ApiService.Instance.IsAuthenticatedAsync();
            if (!isAuthenticated)
            {
                // Show login dialog
                await ShowLoginDialogAsync();
            }
        }

        private async Task ShowLoginDialogAsync()
        {
            var dialog = new ContentDialog
            {
                Title = "Login Required",
                PrimaryButtonText = "Login",
                SecondaryButtonText = "Sign Up",
                DefaultButton = ContentDialogButton.Primary,
                XamlRoot = this.Content.XamlRoot
            };

            var emailBox = new TextBox
            {
                PlaceholderText = "Email",
                Margin = new Thickness(0, 0, 0, 10)
            };

            var passwordBox = new PasswordBox
            {
                PlaceholderText = "Password",
                Margin = new Thickness(0, 0, 0, 10)
            };

            var stackPanel = new StackPanel
            {
                Spacing = 10
            };
            stackPanel.Children.Add(emailBox);
            stackPanel.Children.Add(passwordBox);

            dialog.Content = stackPanel;

            dialog.PrimaryButtonClick += async (sender, args) =>
            {
                var deferral = args.GetDeferral();
                try
                {
                    var success = await ApiService.Instance.LoginAsync(emailBox.Text, passwordBox.Password);
                    if (!success)
                    {
                        args.Cancel = true;
                        var errorDialog = new ContentDialog
                        {
                            Title = "Login Failed",
                            Content = "Invalid email or password. Please try again.",
                            CloseButtonText = "OK",
                            XamlRoot = this.Content.XamlRoot
                        };
                        await errorDialog.ShowAsync();
                    }
                }
                catch (Exception ex)
                {
                    args.Cancel = true;
                    System.Diagnostics.Debug.WriteLine($"Login error: {ex.Message}");
                }
                finally
                {
                    deferral.Complete();
                }
            };

            dialog.SecondaryButtonClick += async (sender, args) =>
            {
                var deferral = args.GetDeferral();
                try
                {
                    // Show signup dialog
                    await ShowSignupDialogAsync();
                }
                finally
                {
                    deferral.Complete();
                }
            };

            await dialog.ShowAsync();
        }

        private async Task ShowSignupDialogAsync()
        {
            var dialog = new ContentDialog
            {
                Title = "Create Account",
                PrimaryButtonText = "Sign Up",
                CloseButtonText = "Cancel",
                DefaultButton = ContentDialogButton.Primary,
                XamlRoot = this.Content.XamlRoot
            };

            var nameBox = new TextBox
            {
                PlaceholderText = "Full Name",
                Margin = new Thickness(0, 0, 0, 10)
            };

            var emailBox = new TextBox
            {
                PlaceholderText = "Email",
                Margin = new Thickness(0, 0, 0, 10)
            };

            var passwordBox = new PasswordBox
            {
                PlaceholderText = "Password",
                Margin = new Thickness(0, 0, 0, 10)
            };

            var stackPanel = new StackPanel
            {
                Spacing = 10
            };
            stackPanel.Children.Add(nameBox);
            stackPanel.Children.Add(emailBox);
            stackPanel.Children.Add(passwordBox);

            dialog.Content = stackPanel;

            dialog.PrimaryButtonClick += async (sender, args) =>
            {
                var deferral = args.GetDeferral();
                try
                {
                    var success = await ApiService.Instance.SignupAsync(nameBox.Text, emailBox.Text, passwordBox.Password);
                    if (!success)
                    {
                        args.Cancel = true;
                        var errorDialog = new ContentDialog
                        {
                            Title = "Signup Failed",
                            Content = "Failed to create account. Please try again.",
                            CloseButtonText = "OK",
                            XamlRoot = this.Content.XamlRoot
                        };
                        await errorDialog.ShowAsync();
                    }
                }
                catch (Exception ex)
                {
                    args.Cancel = true;
                    System.Diagnostics.Debug.WriteLine($"Signup error: {ex.Message}");
                }
                finally
                {
                    deferral.Complete();
                }
            };

            await dialog.ShowAsync();
        }

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

        private void VoiceInputButton_Click(object sender, RoutedEventArgs e)
        {
            if (!_isRecording) StartVoiceInput();
            else StopVoiceInput();
        }

        private void StartVoiceInput()
        {
            try
            {
                // Check if already recording
                if (_isRecording)
                {
                    System.Diagnostics.Debug.WriteLine("Already recording.");
                    return;
                }

                // Dispose any existing instance
                if (_waveIn != null)
                {
                    _waveIn.Dispose();
                    _waveIn = null;
                }

                _waveIn = new WaveInEvent();
                _waveIn.WaveFormat = new WaveFormat(16000, 1); // 16kHz Mono for Speech
                _waveIn.DataAvailable += OnAudioDataAvailable;
                _waveIn.StartRecording();
                _isRecording = true;
                System.Diagnostics.Debug.WriteLine("Voice Recording Started.");
            }
            catch (NAudio.MmException ex)
            {
                System.Diagnostics.Debug.WriteLine($"Microphone access error: {ex.Message}");
                _isRecording = false;
                _waveIn?.Dispose();
                _waveIn = null;
                
                // Show error to user
                this.DispatcherQueue.TryEnqueue(async () =>
                {
                    var dialog = new ContentDialog
                    {
                        Title = "Microphone Access Error",
                        Content = "Unable to access microphone. Please check:\n1. Microphone permissions are enabled\n2. No other application is using the microphone\n3. A microphone is connected and working",
                        CloseButtonText = "OK",
                        XamlRoot = this.Content.XamlRoot
                    };
                    await dialog.ShowAsync();
                });
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Voice recording error: {ex.Message}");
                _isRecording = false;
                _waveIn?.Dispose();
                _waveIn = null;
            }
        }

        private void StopVoiceInput()
        {
            _waveIn?.StopRecording();
            _waveIn?.Dispose();
            _isRecording = false;
        }

        private async void OnAudioDataAvailable(object sender, WaveInEventArgs e)
        {
            if (_speechClient == null) return;

            try
            {
                // Start a bidirectional streaming call
                using var streamingCall = _speechClient.StreamingRecognize();

                // Step 1: Send Configuration
                await streamingCall.WriteAsync(new StreamingRecognizeRequest
                {
                    StreamingConfig = new StreamingRecognitionConfig
                    {
                        Config = new RecognitionConfig
                        {
                            Encoding = RecognitionConfig.Types.AudioEncoding.Linear16,
                            SampleRateHertz = 16000,
                            LanguageCode = "en-US",
                        },
                        InterimResults = true
                    }
                });

                // Step 2: Send Audio Buffer
                await streamingCall.WriteAsync(new StreamingRecognizeRequest
                {
                    AudioContent = Google.Protobuf.ByteString.CopyFrom(e.Buffer, 0, e.BytesRecorded)
                });

                // Step 3: Complete the write for this chunk
                await streamingCall.WriteCompleteAsync();

                // Step 4: Process Results using await foreach (Fixes MoveNext/Current error)
                // 
                await foreach (var response in streamingCall.GetResponseStream())
                {
                    foreach (var result in response.Results)
                    {
                        if (result.Alternatives.Count > 0 && CommandInput != null)
                        {
                            string transcript = result.Alternatives[0].Transcript;

                            // UI elements must be updated on the UI Thread
                            this.DispatcherQueue.TryEnqueue(() =>
                            {
                                CommandInput.Text = transcript;
                            });
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Voice recognition error: {ex.Message}");
            }
        }

        #endregion
    }
}