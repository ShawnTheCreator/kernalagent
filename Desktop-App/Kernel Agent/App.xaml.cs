using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Threading.Tasks;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Controls.Primitives;
using Microsoft.UI.Xaml.Data;
using Microsoft.UI.Xaml.Input;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Navigation;
using Microsoft.UI.Xaml.Shapes;
using Windows.ApplicationModel;
using Windows.ApplicationModel.Activation;
using Windows.Foundation;
using Windows.Foundation.Collections;
using Kernel_Agent.Services;
using Microsoft.Windows.AppNotifications;

// To learn more about WinUI, the WinUI project structure,
// and more about our project templates, see: http://aka.ms/winui-project-info.

namespace Kernel_Agent
{
    /// <summary>
    /// Provides application-specific behavior to supplement the default Application class.
    /// </summary>
    public partial class App : Application
    {
        internal Window? _window;
        internal static SentinelClient? SentinelClient { get; private set; }

        /// <summary>
        /// Initializes the singleton application object.  This is the first line of authored code
        /// executed, and as such is the logical equivalent of main() or WinMain().
        /// </summary>
        public App()
        {
            InitializeComponent();
            
            // Initialize Sentinel client
            SentinelClient = new SentinelClient();

            try
            {
                AppNotificationManager.Default.Register();
                AppNotificationManager.Default.NotificationInvoked += OnNotificationInvoked;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[NOTIFICATIONS] Init failed: {ex.Message}");
            }

            AppDomain.CurrentDomain.ProcessExit += (_, __) =>
            {
                try
                {
                    SentinelClient?.DisconnectAsync().GetAwaiter().GetResult();
                }
                catch
                {
                    // Best-effort shutdown
                }

                try
                {
                    AppNotificationManager.Default.NotificationInvoked -= OnNotificationInvoked;
                }
                catch
                {
                }
            };
            _ = Task.Run(async () => 
            {
                try
                {
                    await SentinelClient.ConnectAsync();
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"Failed to connect Sentinel client: {ex.Message}");
                }
            });
        }

        private static async void OnNotificationInvoked(AppNotificationManager sender, AppNotificationActivatedEventArgs args)
        {
            try
            {
                var parsed = ParseNotificationArguments(args.Argument);
                parsed.TryGetValue("action", out var action);
                parsed.TryGetValue("alertId", out var alertId);

                if (!string.IsNullOrWhiteSpace(action) && !string.IsNullOrWhiteSpace(alertId))
                {
                    await (SentinelClient?.SendUserResponseAsync(alertId, action) ?? Task.CompletedTask);
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[NOTIFICATIONS] Invoke handler failed: {ex.Message}");
            }
        }

        private static Dictionary<string, string> ParseNotificationArguments(string raw)
        {
            var dict = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            if (string.IsNullOrWhiteSpace(raw)) return dict;

            foreach (var part in raw.Split('&', StringSplitOptions.RemoveEmptyEntries))
            {
                var kv = part.Split('=', 2);
                if (kv.Length == 2)
                {
                    dict[Uri.UnescapeDataString(kv[0])] = Uri.UnescapeDataString(kv[1]);
                }
            }

            return dict;
        }

        public Window? GetMainWindow()
        {
            return _window;
        }

        /// <summary>
        /// Invoked when the application is launched.
        /// </summary>
        /// <param name="args">Details about the launch request and process.</param>
        protected override void OnLaunched(Microsoft.UI.Xaml.LaunchActivatedEventArgs args)
        {
            _window = new MainWindow();
            _window.Activate();
        }
    }
}
