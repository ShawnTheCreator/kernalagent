using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Navigation;
using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using Windows.UI;
using Windows.UI.Popups;

namespace Kernel_Agent
{
    public sealed partial class SentinelPage : Page
    {
        private readonly SentinelService _sentinelService;
        private DispatcherTimer _refreshTimer;
        private ObservableCollection<ProcessInfo> _processes;
        private ObservableCollection<SystemAlert> _alerts;

        public SentinelPage()
        {
            this.InitializeComponent();
            
            _sentinelService = SentinelService.Instance;
            _processes = new ObservableCollection<ProcessInfo>();
            _alerts = new ObservableCollection<SystemAlert>();
            
            InitializeUI();
            SetupTimer();
            LoadDataAsync();
        }

        private void InitializeUI()
        {
            ProcessesListView.ItemsSource = _processes;
            AlertsListView.ItemsSource = _alerts;
            
            // Add common applications to suggestions
            AppSuggestBox.ItemsSource = new string[]
            {
                "chrome.exe", "firefox.exe", "msedge.exe",
                "code.exe", "devenv.exe", "notepad++.exe",
                "explorer.exe", "spotify.exe", "discord.exe",
                "slack.exe", "teams.exe", "zoom.exe"
            };
        }

        private void SetupTimer()
        {
            _refreshTimer = new DispatcherTimer
            {
                Interval = TimeSpan.FromSeconds(10) // Refresh every 10 seconds
            };
            _refreshTimer.Tick += async (sender, e) => await LoadDataAsync();
            _refreshTimer.Start();
        }

        private async Task LoadDataAsync()
        {
            try
            {
                RefreshButton.IsEnabled = false;
                RefreshButton.Content = "⏳ Loading...";

                // Get system status
                var statusSummary = await _sentinelService.GetSystemStatusSummaryAsync();
                UpdateSystemStatus(statusSummary);

                // Get top processes
                var topProcesses = await _sentinelService.GetTopProcessesAsync(10);
                UpdateProcessesList(topProcesses);

                // Get alerts
                var alerts = await _sentinelService.GetSystemAlertsAsync();
                UpdateAlertsList(alerts);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SENTINEL_PAGE] LoadData error: {ex.Message}");
                await ShowErrorDialog("Failed to load Sentinel data. Please check if the microservice is running.");
            }
            finally
            {
                RefreshButton.IsEnabled = true;
                RefreshButton.Content = "🔄 Refresh";
            }
        }

        private void UpdateSystemStatus(SystemStatusSummary status)
        {
            // Update metrics
            CpuUsageText.Text = $"{status.CpuUsage:F1}%";
            MemoryUsageText.Text = $"{status.MemoryUsage:F1}%";
            TemperatureText.Text = $"{status.Temperature:F0}°C";
            OverallStatusText.Text = status.Status;
            
            // Update status text
            CpuStatusText.Text = status.CpuStatus;
            MemoryStatusText.Text = status.MemoryStatus;
            ThermalStatusText.Text = status.ThermalStatus;
            
            // Update process count
            var processCountElement = (OverallStatusText.Parent as StackPanel)?.Children[1] as TextBlock;
            if (processCountElement != null)
            {
                processCountElement.Text = $"Processes: {status.ActiveProcesses}";
            }
            
            // Update status bar
            UpdateStatusBar(status);
        }

        private void UpdateStatusBar(SystemStatusSummary status)
        {
            StatusBar.Background = status.StatusColor;
            
            if (status.IsHealthy)
            {
                if (status.AlertCount > 0)
                {
                    StatusMessage.Text = $"System Healthy - {status.AlertCount} alerts";
                }
                else
                {
                    StatusMessage.Text = "System Healthy - All systems normal";
                }
            }
            else
            {
                StatusMessage.Text = $"System Issues Detected - {status.AlertCount} alerts";
            }
        }

        private void UpdateProcessesList(System.Collections.Generic.List<ProcessInfo> processes)
        {
            _processes.Clear();
            foreach (var process in processes.Take(10))
            {
                _processes.Add(process);
            }
        }

        private void UpdateAlertsList(System.Collections.Generic.List<SystemAlert> alerts)
        {
            _alerts.Clear();
            foreach (var alert in alerts.Take(5))
            {
                _alerts.Add(alert);
            }
        }

        private async void RefreshButton_Click(object sender, RoutedEventArgs e)
        {
            await LoadDataAsync();
        }

        private async void OptimizeButton_Click(object sender, RoutedEventArgs e)
        {
            await ShowLoadingDialog("Optimizing system...");
            
            try
            {
                // Kill resource hogs
                var hogResult = await _sentinelService.KillResourceHogsAsync(85.0, 90.0);
                
                // Clean up ghost processes
                var ghostResult = await _sentinelService.CleanupGhostProcessesAsync(1.0);
                
                HideLoadingDialog();
                
                var message = "System optimization complete!\n\n";
                if (hogResult?.Success == true)
                {
                    message += $"• Resource hogs terminated: {hogResult.ProcessesKilled.Count}\n";
                }
                if (ghostResult?.Success == true)
                {
                    message += $"• Ghost processes cleaned: {ghostResult.ProcessesKilled.Count}\n";
                }
                
                await ShowInfoDialog(message);
                await LoadDataAsync(); // Refresh data
            }
            catch (Exception ex)
            {
                HideLoadingDialog();
                await ShowErrorDialog($"Optimization failed: {ex.Message}");
            }
        }

        private async void CleanupButton_Click(object sender, RoutedEventArgs e)
        {
            await ShowLoadingDialog("Cleaning up system...");
            
            try
            {
                var result = await _sentinelService.CleanupGhostProcessesAsync(2.0);
                
                HideLoadingDialog();
                
                if (result?.Success == true)
                {
                    var message = $"Ghost process cleanup complete!\n\n" +
                                 $"• Processes cleaned: {result.ProcessesKilled.Count}\n" +
                                 $"• Processes skipped: {result.ProcessesSkipped.Count}";
                    
                    await ShowInfoDialog(message);
                    await LoadDataAsync(); // Refresh data
                }
                else
                {
                    await ShowErrorDialog("Ghost cleanup failed. Please check system permissions.");
                }
            }
            catch (Exception ex)
            {
                HideLoadingDialog();
                await ShowErrorDialog($"Cleanup failed: {ex.Message}");
            }
        }

        private async void FocusModeButton_Click(object sender, RoutedEventArgs e)
        {
            var targetApp = AppSuggestBox.Text?.Trim();
            if (string.IsNullOrEmpty(targetApp))
            {
                await ShowErrorDialog("Please enter an application name for focus mode.");
                return;
            }

            await ShowLoadingDialog($"Optimizing for {targetApp}...");
            
            try
            {
                var result = await _sentinelService.OptimizeForFocusAsync(targetApp);
                
                HideLoadingDialog();
                
                if (result?.Success == true)
                {
                    var message = $"Focus optimization complete!\n\n" +
                                 $"• Target: {result.TargetApp}\n" +
                                 $"• Actions taken: {result.ActionsTaken.Count}\n" +
                                 $"• Processes adjusted: {result.ProcessesAdjusted.Count}";
                    
                    await ShowInfoDialog(message);
                    await LoadDataAsync(); // Refresh data
                }
                else
                {
                    await ShowErrorDialog($"Focus optimization failed: {result?.Error ?? "Unknown error"}");
                }
            }
            catch (Exception ex)
            {
                HideLoadingDialog();
                await ShowErrorDialog($"Focus mode failed: {ex.Message}");
            }
        }

        private async void PowerSaverButton_Click(object sender, RoutedEventArgs e)
        {
            await SetPowerProfile("power_saver", "Power Saver");
        }

        private async void BalancedButton_Click(object sender, RoutedEventArgs e)
        {
            await SetPowerProfile("balanced", "Balanced");
        }

        private async void HighPerfButton_Click(object sender, RoutedEventArgs e)
        {
            await SetPowerProfile("high_performance", "High Performance");
        }

        private async Task SetPowerProfile(string profile, string displayName)
        {
            await ShowLoadingDialog($"Setting {displayName} power profile...");
            
            try
            {
                var result = await _sentinelService.SetPowerProfileAsync(profile);
                
                HideLoadingDialog();
                
                if (result?.Success == true)
                {
                    await ShowInfoDialog($"Power profile changed to {displayName} successfully!");
                    await LoadDataAsync(); // Refresh data
                }
                else
                {
                    await ShowErrorDialog($"Power profile change failed: {result?.Reason ?? "Unknown error"}");
                }
            }
            catch (Exception ex)
            {
                HideLoadingDialog();
                await ShowErrorDialog($"Power profile change failed: {ex.Message}");
            }
        }

        #region Dialog Helpers

        private ContentDialog? _loadingDialog;

        private async Task ShowLoadingDialog(string message)
        {
            _loadingDialog = new ContentDialog
            {
                Title = "Processing",
                Content = message,
                CloseButtonText = "Cancel"
            };
            
            _loadingDialog.Closed += (sender, args) => _loadingDialog = null;
            await _loadingDialog.ShowAsync();
        }

        private void HideLoadingDialog()
        {
            _loadingDialog?.Hide();
        }

        private async Task ShowInfoDialog(string message)
        {
            var dialog = new ContentDialog
            {
                Title = "Information",
                Content = message,
                CloseButtonText = "OK"
            };
            
            await dialog.ShowAsync();
        }

        private async Task ShowErrorDialog(string message)
        {
            var dialog = new ContentDialog
            {
                Title = "Error",
                Content = message,
                CloseButtonText = "OK"
            };
            
            await dialog.ShowAsync();
        }

        #endregion

        #region Navigation

        protected override void OnNavigatedTo(NavigationEventArgs e)
        {
            base.OnNavigatedTo(e);
        }

        protected override void OnNavigatedFrom(NavigationEventArgs e)
        {
            base.OnNavigatedFrom(e);
            _refreshTimer?.Stop();
        }

        #endregion
    }
}
