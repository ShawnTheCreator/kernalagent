using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;
using System.Threading;
using System.Threading.Tasks;
using Kernel_Agent.Services;

namespace Kernel_Agent
{
    public sealed partial class SettingsPage : Page
    {
        private SettingsService? _settingsInstance;
        private SettingsService _settings => _settingsInstance ??= SettingsService.Instance;
        private bool _isLoading = true;
        private CancellationTokenSource? _voiceDebounceCts;

        public SettingsPage()
        {
            this.InitializeComponent();
        }

        private async void Page_Loaded(object sender, RoutedEventArgs e)
        {
            await LoadSettingsAsync();
        }

        private async Task LoadSettingsAsync()
        {
            _isLoading = true;
            
            // Try to sync from backend first
            ShowSyncStatus("Syncing settings from cloud...");
            var synced = await _settings.SyncFromBackendAsync();
            HideSyncStatus();
            
            if (!synced)
            {
                System.Diagnostics.Debug.WriteLine("[SETTINGS] Using local settings (offline or not logged in)");
            }

            // Load all settings into UI
            LoadSettingsToUI();
            
            _isLoading = false;
        }

        private void LoadSettingsToUI()
        {
            // Appearance
            SelectComboItemByTag(GetControl<ComboBox>("ThemeCombo"), _settings.Theme);
            SelectComboItemByTag(GetControl<ComboBox>("LanguageCombo"), _settings.Language);
            
            // Apply saved theme
            ApplyTheme(_settings.Theme);

            // Execution
            SelectComboItemByTag(GetControl<ComboBox>("ExecutionModeCombo"), _settings.ExecutionMode);
            if (GetControl<ToggleSwitch>("ConfirmActionsToggle") is ToggleSwitch confirm)
                confirm.IsOn = _settings.ConfirmActions;
            if (GetControl<ToggleSwitch>("AutoSaveSkillsToggle") is ToggleSwitch autoSave)
                autoSave.IsOn = _settings.AutoSaveSkills;

            // Voice
            if (GetControl<ToggleSwitch>("VoiceEnabledToggle") is ToggleSwitch voice)
                voice.IsOn = _settings.VoiceEnabled;
            if (GetControl<Slider>("SilenceThresholdSlider") is Slider silThresh)
                silThresh.Value = _settings.SilenceThreshold;
            if (GetControl<Slider>("SilenceDurationSlider") is Slider silDur)
                silDur.Value = _settings.SilenceDurationMs;
            if (GetControl<TextBlock>("SilenceThresholdValue") is TextBlock silThreshVal)
                silThreshVal.Text = $"{_settings.SilenceThreshold}";
            if (GetControl<TextBlock>("SilenceDurationValue") is TextBlock silDurVal)
                silDurVal.Text = $"{_settings.SilenceDurationMs}ms";
            SelectComboItemByTag(GetControl<ComboBox>("VoiceLanguageCombo"), _settings.VoiceLanguage);

            // Notifications
            if (GetControl<ToggleSwitch>("NotificationsToggle") is ToggleSwitch notif)
                notif.IsOn = _settings.NotificationsEnabled;
        }

        private T? GetControl<T>(string name) where T : class
        {
            return FindName(name) as T;
        }

        private void SelectComboItemByTag(ComboBox? combo, string tag)
        {
            if (combo == null) return;
            foreach (ComboBoxItem item in combo.Items)
            {
                if (item.Tag?.ToString() == tag)
                {
                    combo.SelectedItem = item;
                    return;
                }
            }
            if (combo.Items.Count > 0)
                combo.SelectedIndex = 0;
        }

        private void ShowSyncStatus(string message)
        {
            if (GetControl<Border>("SyncStatusBorder") is Border border)
                border.Visibility = Visibility.Visible;
            if (GetControl<TextBlock>("SyncStatusText") is TextBlock text)
                text.Text = message;
        }

        private void HideSyncStatus()
        {
            if (GetControl<Border>("SyncStatusBorder") is Border border)
                border.Visibility = Visibility.Collapsed;
        }

        private async void SaveSettingAndSync()
        {
            if (_isLoading) return;
            await _settings.SyncToBackendAsync();
        }

        private void DebouncedSaveLocalSettings()
        {
            if (_isLoading) return;

            try { _voiceDebounceCts?.Cancel(); } catch { }
            _voiceDebounceCts = new CancellationTokenSource();
            var token = _voiceDebounceCts.Token;

            _ = Task.Run(async () =>
            {
                try
                {
                    await Task.Delay(500, token);
                    if (token.IsCancellationRequested) return;

                    // Voice settings are local-only, so no backend sync.
                }
                catch (OperationCanceledException)
                {
                }
            });
        }

        #region Appearance Event Handlers

        private void ThemeCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_isLoading) return;
            if (sender is ComboBox combo && combo.SelectedItem is ComboBoxItem item && item.Tag != null)
            {
                _settings.Theme = item.Tag.ToString()!;
                ApplyTheme(_settings.Theme);
                SaveSettingAndSync();
            }
        }

        /// <summary>
        /// Apply theme to the app window
        /// </summary>
        private void ApplyTheme(string theme)
        {
            try
            {
                // Use global ThemeManager
                ThemeManager.Instance.ApplyTheme(theme);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SETTINGS] Theme apply error: {ex.Message}");
            }
        }

        private void LanguageCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_isLoading) return;
            if (sender is ComboBox combo && combo.SelectedItem is ComboBoxItem item && item.Tag != null)
            {
                _settings.Language = item.Tag.ToString()!;
                SaveSettingAndSync();
            }
        }

        #endregion

        #region Execution Event Handlers

        private void ExecutionModeCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_isLoading) return;
            if (sender is ComboBox combo && combo.SelectedItem is ComboBoxItem item && item.Tag != null)
            {
                _settings.ExecutionMode = item.Tag.ToString()!;
                SaveSettingAndSync();
            }
        }

        private void ConfirmActionsToggle_Toggled(object sender, RoutedEventArgs e)
        {
            if (_isLoading) return;
            if (sender is ToggleSwitch toggle)
            {
                _settings.ConfirmActions = toggle.IsOn;
                SaveSettingAndSync();
            }
        }

        private void AutoSaveSkillsToggle_Toggled(object sender, RoutedEventArgs e)
        {
            if (_isLoading) return;
            if (sender is ToggleSwitch toggle)
            {
                _settings.AutoSaveSkills = toggle.IsOn;
                SaveSettingAndSync();
            }
        }

        #endregion

        #region Voice Event Handlers

        private void VoiceEnabledToggle_Toggled(object sender, RoutedEventArgs e)
        {
            if (_isLoading) return;
            if (sender is ToggleSwitch toggle)
            {
                _settings.VoiceEnabled = toggle.IsOn;
                DebouncedSaveLocalSettings();
            }
        }

        private void SilenceThresholdSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
        {
            int value = (int)e.NewValue;
            if (GetControl<TextBlock>("SilenceThresholdValue") is TextBlock txt)
                txt.Text = $"{value}";
            if (!_isLoading)
            {
                _settings.SilenceThreshold = value;
                DebouncedSaveLocalSettings();
            }
        }

        private void SilenceDurationSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
        {
            int value = (int)e.NewValue;
            if (GetControl<TextBlock>("SilenceDurationValue") is TextBlock txt)
                txt.Text = $"{value}ms";
            if (!_isLoading)
            {
                _settings.SilenceDurationMs = value;
                DebouncedSaveLocalSettings();
            }
        }

        private void VoiceLanguageCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_isLoading) return;
            if (sender is ComboBox combo && combo.SelectedItem is ComboBoxItem item && item.Tag != null)
            {
                _settings.VoiceLanguage = item.Tag.ToString()!;
                DebouncedSaveLocalSettings();
            }
        }

        #endregion

        #region Notifications Event Handlers

        private void NotificationsToggle_Toggled(object sender, RoutedEventArgs e)
        {
            if (_isLoading) return;
            if (sender is ToggleSwitch toggle)
            {
                _settings.NotificationsEnabled = toggle.IsOn;
                SaveSettingAndSync();
            }
        }

        #endregion

        #region Sync and Reset

        private async void SyncFromCloudButton_Click(object sender, RoutedEventArgs e)
        {
            ShowSyncStatus("Syncing settings from cloud...");
            var success = await _settings.SyncFromBackendAsync();
            HideSyncStatus();

            if (success)
            {
                _isLoading = true;
                LoadSettingsToUI();
                _isLoading = false;
            }

            var dialog = new ContentDialog
            {
                Title = success ? "Sync Complete" : "Sync Failed",
                Content = success ? "Settings synced from cloud." : "Could not sync settings. Check your connection.",
                CloseButtonText = "OK",
                XamlRoot = this.XamlRoot
            };
            await dialog.ShowAsync();
        }

        private async void ResetAllSettingsButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new ContentDialog
            {
                Title = "Reset All Settings",
                Content = "Are you sure you want to reset all settings to defaults?",
                PrimaryButtonText = "Reset",
                CloseButtonText = "Cancel",
                DefaultButton = ContentDialogButton.Close,
                XamlRoot = this.XamlRoot
            };

            var result = await dialog.ShowAsync();
            if (result == ContentDialogResult.Primary)
            {
                _settings.ResetToDefaults();
                _isLoading = true;
                LoadSettingsToUI();
                _isLoading = false;
                await _settings.SyncToBackendAsync();
            }
        }

        #endregion
    }
}
