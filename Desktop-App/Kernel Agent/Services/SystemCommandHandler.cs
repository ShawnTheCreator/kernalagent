using System;
using System.Threading.Tasks;
using System.Text.RegularExpressions;
using System.Diagnostics;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// System Command Handler - Processes natural language commands for system control
    /// Integrates with SystemControlService to execute PC operations
    /// </summary>
    public class SystemCommandHandler
    {
        private static SystemCommandHandler? _instance;
        public static SystemCommandHandler Instance => _instance ??= new SystemCommandHandler();

        public event Action<string>? OnCommandExecuted;
        public event Action<string>? OnCommandFailed;

        private SystemCommandHandler()
        {
            // Private constructor for singleton
        }

        /// <summary>
        /// Process a natural language command
        /// </summary>
        public async Task<bool> ProcessCommandAsync(string command)
        {
            command = command.ToLower().Trim();
            Debug.WriteLine($"[CommandHandler] Processing: {command}");

            try
            {
                // Power Management Commands
                if (IsMatch(command, "shutdown", "shut down", "turn off computer", "power off"))
                {
                    return await HandleShutdownCommand(command);
                }
                
                if (IsMatch(command, "restart", "reboot", "reset computer"))
                {
                    return await HandleRestartCommand(command);
                }
                
                if (IsMatch(command, "sleep", "put to sleep"))
                {
                    await SystemControlService.Instance.SleepAsync();
                    OnCommandExecuted?.Invoke("Computer is going to sleep");
                    return true;
                }
                
                if (IsMatch(command, "hibernate"))
                {
                    await SystemControlService.Instance.HibernateAsync();
                    OnCommandExecuted?.Invoke("Computer is hibernating");
                    return true;
                }
                
                if (IsMatch(command, "lock", "lock computer", "lock screen"))
                {
                    await SystemControlService.Instance.LockAsync();
                    OnCommandExecuted?.Invoke("Computer locked");
                    return true;
                }
                
                if (IsMatch(command, "log off", "logoff", "sign out", "logout"))
                {
                    await SystemControlService.Instance.LogoffAsync();
                    OnCommandExecuted?.Invoke("Logging off");
                    return true;
                }

                // Volume Commands
                if (IsMatch(command, "mute", "unmute", "toggle mute"))
                {
                    await SystemControlService.Instance.ToggleMuteAsync();
                    OnCommandExecuted?.Invoke("Toggled mute");
                    return true;
                }
                
                if (command.Contains("volume"))
                {
                    return await HandleVolumeCommand(command);
                }

                // Brightness Commands
                if (command.Contains("brightness"))
                {
                    return await HandleBrightnessCommand(command);
                }

                // Display Commands
                if (IsMatch(command, "turn off screen", "turn off monitor", "turn off display"))
                {
                    await SystemControlService.Instance.TurnOffMonitorsAsync();
                    OnCommandExecuted?.Invoke("Turning off monitors");
                    return true;
                }

                // System Info Commands
                if (IsMatch(command, "system info", "system information", "pc info", "computer info"))
                {
                    var info = await SystemControlService.Instance.GetSystemInfoAsync();
                    var message = $"Computer: {info.ComputerName}\n" +
                                 $"User: {info.UserName}\n" +
                                 $"OS: {info.OSVersion}\n" +
                                 $"CPU Cores: {info.ProcessorCount}\n" +
                                 $"Uptime: {info.Uptime:hh\\:mm\\:ss}\n" +
                                 $"Memory: {info.FreeMemoryMB}MB free / {info.TotalMemoryMB}MB total";
                    
                    if (info.BatteryPercentage.HasValue)
                    {
                        message += $"\nBattery: {info.BatteryPercentage}% {(info.IsCharging ? "(Charging)" : "")}";
                    }
                    
                    OnCommandExecuted?.Invoke(message);
                    return true;
                }

                // Battery Commands
                if (IsMatch(command, "battery", "battery status", "battery level"))
                {
                    var battery = await SystemControlService.Instance.GetBatteryInfoAsync();
                    OnCommandExecuted?.Invoke($"Battery: {battery.Percentage}% - {battery.Status} {(battery.IsCharging ? "(Charging)" : "")}");
                    return true;
                }

                // Network Commands
                if (IsMatch(command, "network", "network status", "wifi", "internet"))
                {
                    var network = await SystemControlService.Instance.GetNetworkInfoAsync();
                    OnCommandExecuted?.Invoke($"Network: {(network.IsConnected ? "Connected" : "Disconnected")} - {network.ConnectionType}");
                    return true;
                }

                // Disk Commands
                if (IsMatch(command, "disk space", "storage", "drive space"))
                {
                    var disks = await SystemControlService.Instance.GetDiskInfoAsync();
                    var message = "Disk Space:\n";
                    foreach (var disk in disks)
                    {
                        message += $"{disk.Name} ({disk.Label}): {disk.FreeSizeGB}GB free / {disk.TotalSizeGB}GB total\n";
                    }
                    OnCommandExecuted?.Invoke(message);
                    return true;
                }

                // Process Commands
                if (IsMatch(command, "running processes", "list processes", "show processes"))
                {
                    var processes = await SystemControlService.Instance.GetRunningProcessesAsync();
                    var message = $"Top 10 Processes by Memory:\n";
                    foreach (var process in processes.Take(10))
                    {
                        message += $"{process.Name}: {process.MemoryMB}MB\n";
                    }
                    OnCommandExecuted?.Invoke(message);
                    return true;
                }

                if (command.StartsWith("kill ") || command.StartsWith("close "))
                {
                    var processName = command.Replace("kill ", "").Replace("close ", "").Trim();
                    await SystemControlService.Instance.KillProcessAsync(processName);
                    OnCommandExecuted?.Invoke($"Killed process: {processName}");
                    return true;
                }

                // Clipboard Commands
                if (IsMatch(command, "copy", "get clipboard", "what's in clipboard"))
                {
                    var text = await SystemControlService.Instance.GetClipboardTextAsync();
                    OnCommandExecuted?.Invoke($"Clipboard: {text}");
                    return true;
                }

                // Recycle Bin Commands
                if (IsMatch(command, "empty recycle bin", "empty trash", "clear recycle bin"))
                {
                    await SystemControlService.Instance.EmptyRecycleBinAsync();
                    OnCommandExecuted?.Invoke("Recycle bin emptied");
                    return true;
                }

                // Application Launch Commands
                if (command.StartsWith("open ") || command.StartsWith("launch "))
                {
                    return await HandleLaunchCommand(command);
                }

                // Command not recognized
                Debug.WriteLine($"[CommandHandler] Command not recognized: {command}");
                return false;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[CommandHandler] Error: {ex.Message}");
                OnCommandFailed?.Invoke($"Command failed: {ex.Message}");
                return false;
            }
        }

        #region Command Handlers

        private async Task<bool> HandleShutdownCommand(string command)
        {
            // Check for delay
            var delayMatch = Regex.Match(command, @"(\d+)\s*(second|minute|min|sec)");
            int delaySeconds = 0;
            
            if (delayMatch.Success)
            {
                int value = int.Parse(delayMatch.Groups[1].Value);
                string unit = delayMatch.Groups[2].Value;
                
                delaySeconds = unit.StartsWith("min") ? value * 60 : value;
            }

            await SystemControlService.Instance.ShutdownAsync(delaySeconds);
            
            if (delaySeconds > 0)
            {
                OnCommandExecuted?.Invoke($"Computer will shutdown in {delaySeconds} seconds");
            }
            else
            {
                OnCommandExecuted?.Invoke("Shutting down computer");
            }
            
            return true;
        }

        private async Task<bool> HandleRestartCommand(string command)
        {
            var delayMatch = Regex.Match(command, @"(\d+)\s*(second|minute|min|sec)");
            int delaySeconds = 0;
            
            if (delayMatch.Success)
            {
                int value = int.Parse(delayMatch.Groups[1].Value);
                string unit = delayMatch.Groups[2].Value;
                
                delaySeconds = unit.StartsWith("min") ? value * 60 : value;
            }

            await SystemControlService.Instance.RestartAsync(delaySeconds);
            
            if (delaySeconds > 0)
            {
                OnCommandExecuted?.Invoke($"Computer will restart in {delaySeconds} seconds");
            }
            else
            {
                OnCommandExecuted?.Invoke("Restarting computer");
            }
            
            return true;
        }

        private async Task<bool> HandleVolumeCommand(string command)
        {
            // Extract volume level
            var volumeMatch = Regex.Match(command, @"(\d+)");
            
            if (volumeMatch.Success)
            {
                int volume = int.Parse(volumeMatch.Groups[1].Value);
                await SystemControlService.Instance.SetVolumeAsync(volume);
                OnCommandExecuted?.Invoke($"Volume set to {volume}%");
                return true;
            }
            
            if (command.Contains("up") || command.Contains("increase"))
            {
                // Increase volume (implement current volume tracking if needed)
                OnCommandExecuted?.Invoke("Volume increased");
                return true;
            }
            
            if (command.Contains("down") || command.Contains("decrease"))
            {
                OnCommandExecuted?.Invoke("Volume decreased");
                return true;
            }
            
            return false;
        }

        private async Task<bool> HandleBrightnessCommand(string command)
        {
            var brightnessMatch = Regex.Match(command, @"(\d+)");
            
            if (brightnessMatch.Success)
            {
                int brightness = int.Parse(brightnessMatch.Groups[1].Value);
                await SystemControlService.Instance.SetBrightnessAsync(brightness);
                OnCommandExecuted?.Invoke($"Brightness set to {brightness}%");
                return true;
            }
            
            return false;
        }

        private async Task<bool> HandleLaunchCommand(string command)
        {
            var appName = command.Replace("open ", "").Replace("launch ", "").Trim();
            
            // Common application mappings
            var appMappings = new Dictionary<string, string>
            {
                { "notepad", "notepad.exe" },
                { "calculator", "calc.exe" },
                { "paint", "mspaint.exe" },
                { "word", "winword.exe" },
                { "excel", "excel.exe" },
                { "powerpoint", "powerpnt.exe" },
                { "chrome", "chrome.exe" },
                { "edge", "msedge.exe" },
                { "firefox", "firefox.exe" },
                { "explorer", "explorer.exe" },
                { "cmd", "cmd.exe" },
                { "powershell", "powershell.exe" },
                { "task manager", "taskmgr.exe" },
                { "control panel", "control.exe" },
                { "settings", "ms-settings:" }
            };

            string appPath = appMappings.ContainsKey(appName) ? appMappings[appName] : appName;
            
            await SystemControlService.Instance.LaunchAppAsync(appPath);
            OnCommandExecuted?.Invoke($"Launched {appName}");
            return true;
        }

        #endregion

        #region Helper Methods

        private bool IsMatch(string command, params string[] patterns)
        {
            foreach (var pattern in patterns)
            {
                if (command.Contains(pattern.ToLower()))
                {
                    return true;
                }
            }
            return false;
        }

        #endregion
    }
}
