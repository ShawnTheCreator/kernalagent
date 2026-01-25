using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using Windows.System;
using Windows.System.Power;
using Windows.Media.Control;
using Windows.Storage;
using System.Collections.Generic;
using System.Linq;
using System.Management;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// System Control Service - Comprehensive PC control capabilities
    /// Provides power management, system info, media control, and more
    /// </summary>
    public class SystemControlService
    {
        private static SystemControlService? _instance;
        public static SystemControlService Instance => _instance ??= new SystemControlService();

        #region Windows API Imports

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool ExitWindowsEx(uint uFlags, uint dwReason);

        [DllImport("user32.dll")]
        private static extern void LockWorkStation();

        [DllImport("PowrProf.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
        private static extern bool SetSuspendState(bool hibernate, bool forceCritical, bool disableWakeEvent);

        [DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll")]
        private static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr hWnd);

        private const uint EWX_LOGOFF = 0x00000000;
        private const uint EWX_SHUTDOWN = 0x00000001;
        private const uint EWX_REBOOT = 0x00000002;
        private const uint EWX_FORCE = 0x00000004;
        private const uint EWX_POWEROFF = 0x00000008;
        private const uint EWX_FORCEIFHUNG = 0x00000010;

        private const int SW_MINIMIZE = 6;
        private const int SW_MAXIMIZE = 3;
        private const int SW_RESTORE = 9;

        #endregion

        private SystemControlService()
        {
            // Private constructor for singleton
        }

        #region Power Management

        /// <summary>
        /// Shutdown the computer
        /// </summary>
        public async Task<bool> ShutdownAsync(int delaySeconds = 0)
        {
            try
            {
                Debug.WriteLine($"[SystemControl] Shutting down in {delaySeconds} seconds...");
                
                if (delaySeconds > 0)
                {
                    // Use shutdown command with delay
                    var process = new Process
                    {
                        StartInfo = new ProcessStartInfo
                        {
                            FileName = "shutdown",
                            Arguments = $"/s /t {delaySeconds}",
                            CreateNoWindow = true,
                            UseShellExecute = false
                        }
                    };
                    process.Start();
                    return true;
                }
                else
                {
                    // Immediate shutdown
                    return ExitWindowsEx(EWX_SHUTDOWN | EWX_POWEROFF, 0);
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Shutdown failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Restart the computer
        /// </summary>
        public async Task<bool> RestartAsync(int delaySeconds = 0)
        {
            try
            {
                Debug.WriteLine($"[SystemControl] Restarting in {delaySeconds} seconds...");
                
                if (delaySeconds > 0)
                {
                    var process = new Process
                    {
                        StartInfo = new ProcessStartInfo
                        {
                            FileName = "shutdown",
                            Arguments = $"/r /t {delaySeconds}",
                            CreateNoWindow = true,
                            UseShellExecute = false
                        }
                    };
                    process.Start();
                    return true;
                }
                else
                {
                    return ExitWindowsEx(EWX_REBOOT, 0);
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Restart failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Cancel a pending shutdown/restart
        /// </summary>
        public async Task<bool> CancelShutdownAsync()
        {
            try
            {
                var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = "shutdown",
                        Arguments = "/a",
                        CreateNoWindow = true,
                        UseShellExecute = false
                    }
                };
                process.Start();
                Debug.WriteLine("[SystemControl] Shutdown cancelled");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Cancel shutdown failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Put computer to sleep
        /// </summary>
        public async Task<bool> SleepAsync()
        {
            try
            {
                Debug.WriteLine("[SystemControl] Putting computer to sleep...");
                return SetSuspendState(false, true, true);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Sleep failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Hibernate the computer
        /// </summary>
        public async Task<bool> HibernateAsync()
        {
            try
            {
                Debug.WriteLine("[SystemControl] Hibernating computer...");
                return SetSuspendState(true, true, true);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Hibernate failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Lock the workstation
        /// </summary>
        public async Task<bool> LockAsync()
        {
            try
            {
                Debug.WriteLine("[SystemControl] Locking workstation...");
                LockWorkStation();
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Lock failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Log off current user
        /// </summary>
        public async Task<bool> LogoffAsync()
        {
            try
            {
                Debug.WriteLine("[SystemControl] Logging off user...");
                return ExitWindowsEx(EWX_LOGOFF, 0);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Logoff failed: {ex.Message}");
                return false;
            }
        }

        #endregion

        #region System Information

        /// <summary>
        /// Get comprehensive system information
        /// </summary>
        public async Task<SystemInfo> GetSystemInfoAsync()
        {
            var info = new SystemInfo
            {
                ComputerName = Environment.MachineName,
                UserName = Environment.UserName,
                OSVersion = Environment.OSVersion.ToString(),
                ProcessorCount = Environment.ProcessorCount,
                Is64BitOS = Environment.Is64BitOperatingSystem,
                SystemDirectory = Environment.SystemDirectory,
                CurrentDirectory = Environment.CurrentDirectory,
                TickCount = Environment.TickCount64,
                Uptime = TimeSpan.FromMilliseconds(Environment.TickCount64)
            };

            // Get battery status
            try
            {
                var batteryReport = await Windows.Devices.Power.Battery.AggregateBattery.GetReportAsync();
                if (batteryReport != null)
                {
                    info.BatteryPercentage = batteryReport.RemainingCapacityInMilliwattHours.HasValue && 
                                            batteryReport.FullChargeCapacityInMilliwattHours.HasValue
                        ? (int)((double)batteryReport.RemainingCapacityInMilliwattHours.Value / 
                                batteryReport.FullChargeCapacityInMilliwattHours.Value * 100)
                        : null;
                    info.IsCharging = batteryReport.Status == Windows.System.Power.BatteryStatus.Charging;
                }
            }
            catch { }

            // Get memory info
            try
            {
                var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_OperatingSystem");
                foreach (ManagementObject obj in searcher.Get())
                {
                    info.TotalMemoryMB = Convert.ToInt64(obj["TotalVisibleMemorySize"]) / 1024;
                    info.FreeMemoryMB = Convert.ToInt64(obj["FreePhysicalMemory"]) / 1024;
                }
            }
            catch { }

            return info;
        }

        /// <summary>
        /// Get battery status
        /// </summary>
        public async Task<BatteryInfo> GetBatteryInfoAsync()
        {
            try
            {
                var battery = Windows.Devices.Power.Battery.AggregateBattery;
                var report = await battery.GetReportAsync();

                return new BatteryInfo
                {
                    Percentage = report.RemainingCapacityInMilliwattHours.HasValue && 
                                report.FullChargeCapacityInMilliwattHours.HasValue
                        ? (int)((double)report.RemainingCapacityInMilliwattHours.Value / 
                                report.FullChargeCapacityInMilliwattHours.Value * 100)
                        : 0,
                    IsCharging = report.Status == Windows.System.Power.BatteryStatus.Charging,
                    Status = report.Status.ToString()
                };
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Get battery info failed: {ex.Message}");
                return new BatteryInfo { Percentage = 0, IsCharging = false, Status = "Unknown" };
            }
        }

        #endregion

        #region Volume Control

        /// <summary>
        /// Set system volume (0-100)
        /// </summary>
        public async Task<bool> SetVolumeAsync(int volume)
        {
            try
            {
                volume = Math.Clamp(volume, 0, 100);
                var volumeLevel = volume / 100.0 * 65535;
                
                var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = "powershell",
                        Arguments = $"-Command \"(New-Object -ComObject WScript.Shell).SendKeys([char]174)\"",
                        CreateNoWindow = true,
                        UseShellExecute = false
                    }
                };
                
                Debug.WriteLine($"[SystemControl] Setting volume to {volume}%");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Set volume failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Mute/unmute system volume
        /// </summary>
        public async Task<bool> ToggleMuteAsync()
        {
            try
            {
                var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = "powershell",
                        Arguments = "-Command \"(New-Object -ComObject WScript.Shell).SendKeys([char]173)\"",
                        CreateNoWindow = true,
                        UseShellExecute = false
                    }
                };
                process.Start();
                Debug.WriteLine("[SystemControl] Toggled mute");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Toggle mute failed: {ex.Message}");
                return false;
            }
        }

        #endregion

        #region Display Control

        /// <summary>
        /// Set screen brightness (0-100)
        /// </summary>
        public async Task<bool> SetBrightnessAsync(int brightness)
        {
            try
            {
                brightness = Math.Clamp(brightness, 0, 100);
                
                var searcher = new ManagementObjectSearcher("root\\WMI", "SELECT * FROM WmiMonitorBrightnessMethods");
                foreach (ManagementObject obj in searcher.Get())
                {
                    obj.InvokeMethod("WmiSetBrightness", new object[] { 1, brightness });
                }
                
                Debug.WriteLine($"[SystemControl] Set brightness to {brightness}%");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Set brightness failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Turn off monitors
        /// </summary>
        public async Task<bool> TurnOffMonitorsAsync()
        {
            try
            {
                var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = "powershell",
                        Arguments = "-Command \"(Add-Type '[DllImport(\\\"user32.dll\\\")]public static extern int SendMessage(int hWnd,int hMsg,int wParam,int lParam);' -Name a -Pas)::SendMessage(-1,0x0112,0xF170,2)\"",
                        CreateNoWindow = true,
                        UseShellExecute = false
                    }
                };
                process.Start();
                Debug.WriteLine("[SystemControl] Turned off monitors");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Turn off monitors failed: {ex.Message}");
                return false;
            }
        }

        #endregion

        #region Process Management

        /// <summary>
        /// Get list of running processes
        /// </summary>
        public async Task<List<ProcessInfo>> GetRunningProcessesAsync()
        {
            var processes = new List<ProcessInfo>();
            
            try
            {
                foreach (var process in Process.GetProcesses())
                {
                    try
                    {
                        processes.Add(new ProcessInfo
                        {
                            Id = process.Id,
                            Name = process.ProcessName,
                            WindowTitle = process.MainWindowTitle,
                            MemoryMB = process.WorkingSet64 / 1024 / 1024,
                            StartTime = process.StartTime
                        });
                    }
                    catch { }
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Get processes failed: {ex.Message}");
            }
            
            return processes.OrderByDescending(p => p.MemoryMB).ToList();
        }

        /// <summary>
        /// Kill a process by name
        /// </summary>
        public async Task<bool> KillProcessAsync(string processName)
        {
            try
            {
                var processes = Process.GetProcessesByName(processName);
                foreach (var process in processes)
                {
                    process.Kill();
                }
                Debug.WriteLine($"[SystemControl] Killed process: {processName}");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Kill process failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Launch an application
        /// </summary>
        public async Task<bool> LaunchAppAsync(string appPath, string arguments = "")
        {
            try
            {
                var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = appPath,
                        Arguments = arguments,
                        UseShellExecute = true
                    }
                };
                process.Start();
                Debug.WriteLine($"[SystemControl] Launched app: {appPath}");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Launch app failed: {ex.Message}");
                return false;
            }
        }

        #endregion

        #region Clipboard Operations

        /// <summary>
        /// Get clipboard text
        /// </summary>
        public async Task<string> GetClipboardTextAsync()
        {
            try
            {
                var dataPackage = Windows.ApplicationModel.DataTransfer.Clipboard.GetContent();
                if (dataPackage.Contains(Windows.ApplicationModel.DataTransfer.StandardDataFormats.Text))
                {
                    return await dataPackage.GetTextAsync();
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Get clipboard failed: {ex.Message}");
            }
            return string.Empty;
        }

        /// <summary>
        /// Set clipboard text
        /// </summary>
        public async Task<bool> SetClipboardTextAsync(string text)
        {
            try
            {
                var dataPackage = new Windows.ApplicationModel.DataTransfer.DataPackage();
                dataPackage.SetText(text);
                Windows.ApplicationModel.DataTransfer.Clipboard.SetContent(dataPackage);
                Debug.WriteLine("[SystemControl] Set clipboard text");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Set clipboard failed: {ex.Message}");
                return false;
            }
        }

        #endregion

        #region Network Operations

        /// <summary>
        /// Get network status
        /// </summary>
        public async Task<NetworkInfo> GetNetworkInfoAsync()
        {
            try
            {
                var profile = Windows.Networking.Connectivity.NetworkInformation.GetInternetConnectionProfile();
                
                return new NetworkInfo
                {
                    IsConnected = profile != null,
                    ConnectionType = profile?.NetworkAdapter?.IanaInterfaceType.ToString() ?? "Unknown",
                    SignalStrength = profile?.GetSignalBars()?.ToString() ?? "Unknown"
                };
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Get network info failed: {ex.Message}");
                return new NetworkInfo { IsConnected = false, ConnectionType = "Unknown", SignalStrength = "Unknown" };
            }
        }

        #endregion

        #region File System Operations

        /// <summary>
        /// Empty recycle bin
        /// </summary>
        public async Task<bool> EmptyRecycleBinAsync()
        {
            try
            {
                var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = "cmd.exe",
                        Arguments = "/c rd /s /q %systemdrive%\\$Recycle.bin",
                        CreateNoWindow = true,
                        UseShellExecute = false
                    }
                };
                process.Start();
                await process.WaitForExitAsync();
                Debug.WriteLine("[SystemControl] Emptied recycle bin");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Empty recycle bin failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Get disk space information
        /// </summary>
        public async Task<List<DiskInfo>> GetDiskInfoAsync()
        {
            var disks = new List<DiskInfo>();
            
            try
            {
                foreach (var drive in System.IO.DriveInfo.GetDrives())
                {
                    if (drive.IsReady)
                    {
                        disks.Add(new DiskInfo
                        {
                            Name = drive.Name,
                            Label = drive.VolumeLabel,
                            TotalSizeGB = drive.TotalSize / 1024 / 1024 / 1024,
                            FreeSizeGB = drive.AvailableFreeSpace / 1024 / 1024 / 1024,
                            DriveType = drive.DriveType.ToString()
                        });
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SystemControl] Get disk info failed: {ex.Message}");
            }
            
            return disks;
        }

        #endregion
    }

    #region Data Models

    public class SystemInfo
    {
        public string? ComputerName { get; set; }
        public string? UserName { get; set; }
        public string? OSVersion { get; set; }
        public int ProcessorCount { get; set; }
        public bool Is64BitOS { get; set; }
        public string? SystemDirectory { get; set; }
        public string? CurrentDirectory { get; set; }
        public long TickCount { get; set; }
        public TimeSpan Uptime { get; set; }
        public int? BatteryPercentage { get; set; }
        public bool IsCharging { get; set; }
        public long TotalMemoryMB { get; set; }
        public long FreeMemoryMB { get; set; }
    }

    public class BatteryInfo
    {
        public int Percentage { get; set; }
        public bool IsCharging { get; set; }
        public string? Status { get; set; }
    }

    public class ProcessInfo
    {
        public int Id { get; set; }
        public string? Name { get; set; }
        public string? WindowTitle { get; set; }
        public long MemoryMB { get; set; }
        public DateTime StartTime { get; set; }
    }

    public class NetworkInfo
    {
        public bool IsConnected { get; set; }
        public string? ConnectionType { get; set; }
        public string? SignalStrength { get; set; }
    }

    public class DiskInfo
    {
        public string? Name { get; set; }
        public string? Label { get; set; }
        public long TotalSizeGB { get; set; }
        public long FreeSizeGB { get; set; }
        public string? DriveType { get; set; }
    }

    #endregion
}
