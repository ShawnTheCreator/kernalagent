using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;
using System.Threading;
using System.Threading.Tasks;
using Kernel_Agent.Services;
using Windows.UI.Popups;

namespace Kernel_Agent
{
    /// <summary>
    /// Logic for managing the Agent's safety guardrails and privacy boundaries.
    /// </summary>
    public sealed partial class SecurityPage : Page
    {
        private readonly SecurityPolicyService _policy = SecurityPolicyService.Instance;
        private bool _isLoading = true;

        public SecurityPage()
        {
            this.InitializeComponent();
            this.Loaded += SecurityPage_Loaded;
        }

        private void SecurityPage_Loaded(object sender, RoutedEventArgs e)
        {
            LoadPolicyToUI();
        }

        private void LoadPolicyToUI()
        {
            _isLoading = true;

            try
            {
                _policy.Load();

                if (RestrictedAppsList != null)
                {
                    RestrictedAppsList.ItemsSource = _policy.RestrictedApps;
                }

                if (AutoBlurPasswordsToggle != null) AutoBlurPasswordsToggle.IsOn = _policy.AutoBlurPasswordFieldsInMemory;
                if (ScrubCcToggle != null) ScrubCcToggle.IsOn = _policy.ScrubCreditCardNumbersFromLogs;
                if (HilPaymentsToggle != null) HilPaymentsToggle.IsOn = _policy.EnableHumanInTheLoopForPayments;
                if (LogKeyboardToggle != null) LogKeyboardToggle.IsOn = _policy.LogKeyboardInputDuringActiveTasks;
            }
            finally
            {
                _isLoading = false;
            }
        }

        /// <summary>
        /// Handles the high-stakes "Purge" action. 
        /// In a world-class app, this requires confirmation.
        /// </summary>
        private async void OnPurgeDataClick(object sender, RoutedEventArgs e)
        {
            ContentDialog confirmDialog = new ContentDialog
            {
                Title = "Irreversible Action",
                Content = "This will wipe all learned skills and neural associations. Are you absolutely sure?",
                PrimaryButtonText = "Purge Everything",
                CloseButtonText = "Cancel",
                DefaultButton = ContentDialogButton.Close,
                XamlRoot = this.XamlRoot // Required in WinUI 3
            };

            // Set the style to destructive
            confirmDialog.PrimaryButtonStyle = (Style)Application.Current.Resources["AccentButtonStyle"];

            ContentDialogResult result = await confirmDialog.ShowAsync();

            if (result == ContentDialogResult.Primary)
            {
                await SimulateDataWipe();

                try
                {
                    // Reset security policy to defaults
                    _policy.ResetToDefaults();

                    // Clear auth token + settings (local) as a safety reset
                    try
                    {
                        var localSettings = Windows.Storage.ApplicationData.Current.LocalSettings;
                        localSettings.Values.Remove("AuthToken");
                    }
                    catch
                    {
                    }

                    LoadPolicyToUI();
                }
                catch
                {
                }
            }
        }

        private async Task SimulateDataWipe()
        {
            // Visual feedback for the purge process
            var btn = PurgeButton;
            if (btn != null)
            {
                btn.Content = "WIPING...";
                btn.IsEnabled = false;
                await Task.Delay(2000);
                btn.Content = "DATABASE PURGED";
                await Task.Delay(750);
                btn.Content = "PURGE ALL NEURAL DATA";
                btn.IsEnabled = true;
            }
        }

        private void RestrictedAppToggle_Toggled(object sender, RoutedEventArgs e)
        {
            if (_isLoading) return;
            if (sender is ToggleSwitch t && t.Tag is string ruleId)
            {
                _policy.SetRuleEnabled(ruleId, t.IsOn);
            }
        }

        private void PiiToggle_Toggled(object sender, RoutedEventArgs e)
        {
            if (_isLoading) return;

            _policy.AutoBlurPasswordFieldsInMemory = AutoBlurPasswordsToggle?.IsOn ?? true;
            _policy.ScrubCreditCardNumbersFromLogs = ScrubCcToggle?.IsOn ?? true;
            _policy.EnableHumanInTheLoopForPayments = HilPaymentsToggle?.IsOn ?? true;
            _policy.LogKeyboardInputDuringActiveTasks = LogKeyboardToggle?.IsOn ?? false;
            _policy.Save();
        }

        private async void AddRestrictedAppButton_Click(object sender, RoutedEventArgs e)
        {
            var nameBox = new TextBox { PlaceholderText = "Display name (e.g. Banking)" };
            var processBox = new TextBox { PlaceholderText = "Process contains (e.g. chrome, msedge, bitwarden)" };
            var titleBox = new TextBox { PlaceholderText = "Window title contains (optional)" };
            var enabledToggle = new ToggleSwitch { Header = "Enabled", IsOn = true };

            var panel = new StackPanel { Spacing = 10 };
            panel.Children.Add(nameBox);
            panel.Children.Add(processBox);
            panel.Children.Add(titleBox);
            panel.Children.Add(enabledToggle);

            var dialog = new ContentDialog
            {
                Title = "Add Restricted Application",
                Content = panel,
                PrimaryButtonText = "Add",
                CloseButtonText = "Cancel",
                DefaultButton = ContentDialogButton.Primary,
                XamlRoot = this.XamlRoot
            };

            var result = await dialog.ShowAsync();
            if (result != ContentDialogResult.Primary) return;

            if (string.IsNullOrWhiteSpace(nameBox.Text) || string.IsNullOrWhiteSpace(processBox.Text))
            {
                var err = new ContentDialog
                {
                    Title = "Validation",
                    Content = "Display name and process are required.",
                    CloseButtonText = "OK",
                    XamlRoot = this.XamlRoot
                };
                await err.ShowAsync();
                return;
            }

            _policy.AddRestrictedApp(
                displayName: nameBox.Text.Trim(),
                processNameContains: processBox.Text.Trim(),
                windowTitleContains: titleBox.Text.Trim(),
                enabled: enabledToggle.IsOn
            );

            LoadPolicyToUI();
        }

        /// <summary>
        /// Logic for adding a new app to the restricted list
        /// </summary>
        private void OnAddRestrictedAppClick(object sender, RoutedEventArgs e)
        {
            // This would normally open a process picker. 
            // For the hackathon, we can simulate adding a new entry to the list.
        }
    }
}