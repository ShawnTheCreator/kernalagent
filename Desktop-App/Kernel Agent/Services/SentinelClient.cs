using System;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Notifications;
using System.Runtime.InteropServices;

namespace KernelAgent.Services
{
    public class SentinelClient
    {
        private ClientWebSocket _webSocket;
        private CancellationTokenSource _cancellationTokenSource;
        private readonly string _serverUrl;
        private readonly string _userId;
        private BatteryMonitor _batteryMonitor;
        
        public event Action<SentinelAlert> OnAlertReceived;
        public event Action<int> OnHealthScoreUpdated;
        
        public SentinelClient(string serverUrl = "ws://localhost:8000/ws/sentinel", string userId = "default_user")
        {
            _serverUrl = $"{serverUrl}?user_id={userId}";
            _userId = userId;
            _batteryMonitor = new BatteryMonitor();
        }
        
        public async Task ConnectAsync()
        {
            try
            {
                _webSocket = new ClientWebSocket();
                _cancellationTokenSource = new CancellationTokenSource();
                
                await _webSocket.ConnectAsync(new Uri(_serverUrl), _cancellationTokenSource.Token);
                
                // Start listening for messages
                _ = Task.Run(ListenForMessagesAsync);
                
                // Send initial profile with battery awareness
                await SendUserProfile();
                
                System.Diagnostics.Debug.WriteLine("[Sentinel] Connected to WebSocket");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[Sentinel] Connection failed: {ex.Message}");
            }
        }
        
        public async Task DisconnectAsync()
        {
            try
            {
                _cancellationTokenSource?.Cancel();
                if (_webSocket?.State == WebSocketState.Open)
                {
                    await _webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[Sentinel] Disconnect error: {ex.Message}");
            }
        }
        
        private async Task ListenForMessagesAsync()
        {
            var buffer = new byte[4096];
            
            while (_webSocket.State == WebSocketState.Open && !_cancellationTokenSource.Token.IsCancellationRequested)
            {
                try
                {
                    var result = await _webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), _cancellationTokenSource.Token);
                    
                    if (result.MessageType == WebSocketMessageType.Text)
                    {
                        var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                        ProcessMessage(message);
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[Sentinel] Message receive error: {ex.Message}");
                    break;
                }
            }
        }
        
        private void ProcessMessage(string message)
        {
            try
            {
                using var document = JsonDocument.Parse(message);
                var root = document.RootElement;
                var messageType = root.GetProperty("type").GetString();
                
                switch (messageType)
                {
                    case "sentinel_alert":
                        var alert = JsonSerializer.Deserialize<SentinelAlert>(message);
                        OnAlertReceived?.Invoke(alert);
                        ShowWindowsNotification(alert);
                        break;
                        
                    case "sentinel_health_score":
                        var score = root.GetProperty("score").GetInt32();
                        OnHealthScoreUpdated?.Invoke(score);
                        break;
                        
                    case "sentinel_status":
                        System.Diagnostics.Debug.WriteLine($"[Sentinel] Status: {message}");
                        break;
                        
                    case "sentinel_cleanup_completed":
                        ShowCleanupNotification(root.GetProperty("actions_executed").GetInt32());
                        break;
                        
                    case "sentinel_maintenance_completed":
                        ShowMaintenanceNotification(root.GetProperty("task").GetString());
                        break;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[Sentinel] Message processing error: {ex.Message}");
            }
        }
        
        private void ShowWindowsNotification(SentinelAlert alert)
        {
            var toast = new ToastContentBuilder()
                .AddText($"🛡️ Sentinel Alert")
                .AddText(alert.Message)
                .AddText($"Severity: {alert.Severity.ToUpper()}")
                .AddButton(new ToastButton()
                    .SetContent("Ignore")
                    .AddArgument("action", "ignore")
                    .AddArgument("alertId", alert.Id))
                .AddButton(new ToastButton()
                    .SetContent("Investigate")
                    .AddArgument("action", "investigate")
                    .AddArgument("alertId", alert.Id));
            
            // Add action buttons based on alert type
            if (alert.Suggestions.Contains("kill_processes"))
            {
                toast.AddButton(new ToastButton()
                    .SetContent("Kill Processes")
                    .AddArgument("action", "kill_processes")
                    .AddArgument("alertId", alert.Id));
            }
            
            if (alert.Suggestions.Contains("cleanup"))
            {
                toast.AddButton(new ToastButton()
                    .SetContent("Run Cleanup")
                    .AddArgument("action", "cleanup")
                    .AddArgument("alertId", alert.Id));
            }
            
            var notification = new ToastNotification(toast.GetXml());
            notification.Activated += Notification_Activated;
            ToastNotificationManager.CreateToastNotifier("Kernel Agent").Show(notification);
        }
        
        private void ShowCleanupNotification(int actionsExecuted)
        {
            var toast = new ToastContentBuilder()
                .AddText("🧹 Cleanup Completed")
                .AddText($"Executed {actionsExecuted} cleanup actions")
                .AddText("Your system is now optimized");
            
            var notification = new ToastNotification(toast.GetXml());
            ToastNotificationManager.CreateToastNotifier("Kernel Agent").Show(notification);
        }
        
        private void ShowMaintenanceNotification(string task)
        {
            var toast = new ToastContentBuilder()
                .AddText("🔧 Maintenance Completed")
                .AddText($"Task: {task}")
                .AddText("System maintenance completed successfully");
            
            var notification = new ToastNotification(toast.GetXml());
            ToastNotificationManager.CreateToastNotifier("Kernel Agent").Show(notification);
        }
        
        private async void Notification_Activated(ToastNotification sender, object args)
        {
            try
            {
                var toastArgs = args as ToastActivatedEventArgs;
                var action = toastArgs.Arguments["action"];
                var alertId = toastArgs.Arguments["alertId"];
                
                await SendUserResponse(alertId, action);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[Sentinel] Notification action error: {ex.Message}");
            }
        }
        
        private async Task SendUserResponse(string alertId, string action)
        {
            try
            {
                var response = new
                {
                    type = "sentinel_action",
                    alert_id = alertId,
                    action = action,
                    approved = true
                };
                
                var message = JsonSerializer.Serialize(response);
                var buffer = Encoding.UTF8.GetBytes(message);
                
                await _webSocket.SendAsync(new ArraySegment<byte>(buffer), WebSocketMessageType.Text, true, CancellationToken.None);
                
                System.Diagnostics.Debug.WriteLine($"[Sentinel] Sent response: {action} for alert {alertId}");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[Sentinel] Send response error: {ex.Message}");
            }
        }
        
        private async Task SendUserProfile()
        {
            try
            {
                var profile = new
                {
                    type = "update_profile",
                    profile = new
                    {
                        work_hours = new[] { 9, 17 },
                        gaming_mode = false,
                        notifications = true,
                        battery_aware = true,
                        battery_thresholds = _batteryMonitor.GetBatteryAwareThresholds()
                    }
                };
                
                var message = JsonSerializer.Serialize(profile);
                var buffer = Encoding.UTF8.GetBytes(message);
                
                await _webSocket.SendAsync(new ArraySegment<byte>(buffer), WebSocketMessageType.Text, true, CancellationToken.None);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[Sentinel] Send profile error: {ex.Message}");
            }
        }
        
        public async Task UpdateBatteryStatus()
        {
            if (_webSocket?.State == WebSocketState.Open)
            {
                await SendUserProfile();
            }
        }
    }
    
    public class SentinelAlert
    {
        public string Id { get; set; }
        public string Type { get; set; }
        public string Severity { get; set; }
        public string Message { get; set; }
        public double CurrentValue { get; set; }
        public double Threshold { get; set; }
        public DateTime Timestamp { get; set; }
        public List<string> Suggestions { get; set; }
        public List<Dictionary<string, object>> Processes { get; set; }
    }
    
    public class BatteryMonitor
    {
        [DllImport("kernel32.dll")]
        static extern bool GetSystemPowerStatus(ref SYSTEM_POWER_STATUS sps);
        
        [StructLayout(LayoutKind.Sequential)]
        public struct SYSTEM_POWER_STATUS
        {
            public byte ACLineStatus;
            public byte BatteryFlag;
            public byte BatteryLifePercent;
            public byte SystemStatusFlag;
            public uint BatteryLifeTime;
            public uint BatteryFullLifeTime;
        }
        
        public bool IsOnBattery { get; private set; }
        public int BatteryPercentage { get; private set; }
        
        public void Update()
        {
            try
            {
                var sps = new SYSTEM_POWER_STATUS();
                if (GetSystemPowerStatus(ref sps))
                {
                    IsOnBattery = sps.ACLineStatus == 0; // 0 = Offline, 1 = On AC power
                    BatteryPercentage = sps.BatteryLifePercent == 255 ? -1 : sps.BatteryLifePercent;
                }
            }
            catch
            {
                // Fallback values
                IsOnBattery = false;
                BatteryPercentage = 100;
            }
        }
        
        public Dictionary<string, int> GetBatteryAwareThresholds()
        {
            Update();
            
            // More lenient thresholds when on battery to save power
            if (IsOnBattery)
            {
                return new Dictionary<string, int>
                {
                    { "cpu", 95 },      // Higher CPU threshold on battery
                    { "memory", 98 },   // Higher memory threshold
                    { "temperature", 90 }, // Same temperature threshold
                    { "disk", 95 }      // Same disk threshold
                };
            }
            else
            {
                // Normal thresholds when plugged in
                return new Dictionary<string, int>
                {
                    { "cpu", 90 },
                    { "memory", 95 },
                    { "temperature", 85 },
                    { "disk", 90 }
                };
            }
        }
    }
}
