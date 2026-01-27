using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.UI.Xaml.Media;
using Windows.UI;
using System.Linq;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Sentinel Service - Manages hardware monitoring and PC optimization
    /// The "Nervous System" of the PC - provides real-time system awareness
    /// </summary>
    public class SentinelService
    {
        private static SentinelService? _instance;
        private readonly ApiService _apiService;
        private SentinelHealthReport? _lastHealthReport;
        private SentinelMetrics? _lastMetrics;
        private DateTime _lastUpdate = DateTime.MinValue;
        
        public static SentinelService Instance
        {
            get
            {
                if (_instance == null)
                {
                    _instance = new SentinelService();
                }
                return _instance;
            }
        }

        private SentinelService()
        {
            _apiService = ApiService.Instance;
        }

        /// <summary>
        /// Get comprehensive system health report
        /// </summary>
        public async Task<SentinelHealthReport?> GetHealthReportAsync(bool forceRefresh = false)
        {
            try
            {
                // Cache for 30 seconds to avoid excessive API calls
                if (!forceRefresh && _lastHealthReport != null && 
                    DateTime.Now - _lastUpdate < TimeSpan.FromSeconds(30))
                {
                    return _lastHealthReport;
                }

                var report = await _apiService.GetSentinelHealthReportAsync();
                if (report != null)
                {
                    _lastHealthReport = report;
                    _lastUpdate = DateTime.Now;
                    System.Diagnostics.Debug.WriteLine($"[SENTINEL] Health report updated: CPU {report.Cpu.PercentTotal}%, RAM {report.Memory.Virtual.PercentUsed}%");
                }
                
                return report;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SENTINEL] GetHealthReport error: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Optimize system for a specific application (focus mode)
        /// </summary>
        public async Task<SentinelOptimizationResult?> OptimizeForFocusAsync(string targetApp)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"[SENTINEL] Optimizing for focus: {targetApp}");
                
                var result = await _apiService.OptimizeForFocusAsync(targetApp);
                
                if (result != null && result.Success)
                {
                    System.Diagnostics.Debug.WriteLine($"[SENTINEL] Focus optimization successful: {result.ActionsTaken.Count} actions");
                }
                
                return result;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SENTINEL] OptimizeForFocus error: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Kill resource hog processes
        /// </summary>
        public async Task<SentinelCleanupResult?> KillResourceHogsAsync(double cpuThreshold = 90.0, double memoryThreshold = 95.0)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"[SENTINEL] Killing resource hogs: CPU>{cpuThreshold}%, RAM>{memoryThreshold}%");
                
                var result = await _apiService.KillResourceHogsAsync(cpuThreshold, memoryThreshold);
                
                if (result != null && result.Success)
                {
                    System.Diagnostics.Debug.WriteLine($"[SENTINEL] Resource cleanup successful: {result.ProcessesKilled.Count} killed");
                }
                
                return result;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SENTINEL] KillResourceHogs error: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Clean up ghost (idle) processes
        /// </summary>
        public async Task<SentinelCleanupResult?> CleanupGhostProcessesAsync(double idleHours = 2.0)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"[SENTINEL] Cleaning ghost processes: idle > {idleHours}h");
                
                var result = await _apiService.CleanupGhostProcessesAsync(idleHours);
                
                if (result != null && result.Success)
                {
                    System.Diagnostics.Debug.WriteLine($"[SENTINEL] Ghost cleanup successful: {result.ProcessesKilled.Count} cleaned");
                }
                
                return result;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SENTINEL] CleanupGhostProcesses error: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Set Windows power profile
        /// </summary>
        public async Task<SentinelPowerResult?> SetPowerProfileAsync(string profile)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"[SENTINEL] Setting power profile: {profile}");
                
                var result = await _apiService.SetPowerProfileAsync(profile);
                
                if (result != null && result.Success)
                {
                    System.Diagnostics.Debug.WriteLine($"[SENTINEL] Power profile changed: {profile}");
                }
                
                return result;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SENTINEL] SetPowerProfile error: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Get Sentinel Agent metrics and status
        /// </summary>
        public async Task<SentinelMetrics?> GetMetricsAsync()
        {
            try
            {
                var metrics = await _apiService.GetSentinelMetricsAsync();
                if (metrics != null)
                {
                    _lastMetrics = metrics;
                }
                
                return metrics;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SENTINEL] GetMetrics error: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Get system status summary for UI display
        /// </summary>
        public async Task<SystemStatusSummary> GetSystemStatusSummaryAsync()
        {
            var report = await GetHealthReportAsync();
            if (report == null)
            {
                return new SystemStatusSummary
                {
                    IsHealthy = false,
                    Status = "Unknown",
                    CpuUsage = 0,
                    MemoryUsage = 0,
                    Temperature = 0,
                    ActiveProcesses = 0,
                    AlertCount = 0,
                    StatusColor = new SolidColorBrush(Color.FromArgb(255, 169, 169, 169)) // Gray
                };
            }

            var cpuStatus = GetCpuStatus(report.Cpu.PercentTotal);
            var memoryStatus = GetMemoryStatus(report.Memory.Virtual.PercentUsed);
            var tempStatus = GetTemperatureStatus(report.Temperature.MaxTemp ?? 0);
            
            var overallStatus = GetOverallStatus(cpuStatus, memoryStatus, tempStatus);
            var statusColor = GetStatusColor(overallStatus);

            return new SystemStatusSummary
            {
                IsHealthy = overallStatus != SystemHealthStatus.Critical,
                Status = overallStatus.ToString(),
                CpuUsage = report.Cpu.PercentTotal,
                MemoryUsage = report.Memory.Virtual.PercentUsed,
                Temperature = report.Temperature.MaxTemp ?? 0,
                ActiveProcesses = report.Processes.Count,
                AlertCount = report.Alerts.Count,
                StatusColor = statusColor,
                CpuStatus = cpuStatus.ToString(),
                MemoryStatus = memoryStatus.ToString(),
                ThermalStatus = tempStatus.ToString()
            };
        }

        /// <summary>
        /// Get top resource consuming processes
        /// </summary>
        public async Task<List<ProcessInfo>> GetTopProcessesAsync(int count = 10)
        {
            var report = await GetHealthReportAsync();
            if (report?.Processes == null) return new List<ProcessInfo>();

            return report.Processes
                .OrderByDescending(p => p.CpuPercent + p.MemoryPercent)
                .Take(count)
                .ToList();
        }

        /// <summary>
        /// Get system alerts
        /// </summary>
        public async Task<List<SystemAlert>> GetSystemAlertsAsync()
        {
            var report = await GetHealthReportAsync();
            return report?.Alerts ?? new List<SystemAlert>();
        }

        #region Private Helper Methods

        private SystemHealthStatus GetCpuStatus(double cpuUsage)
        {
            if (cpuUsage > 95) return SystemHealthStatus.Critical;
            if (cpuUsage > 80) return SystemHealthStatus.Warning;
            return SystemHealthStatus.Normal;
        }

        private SystemHealthStatus GetMemoryStatus(double memoryUsage)
        {
            if (memoryUsage > 95) return SystemHealthStatus.Critical;
            if (memoryUsage > 85) return SystemHealthStatus.Warning;
            return SystemHealthStatus.Normal;
        }

        private SystemHealthStatus GetTemperatureStatus(double temperature)
        {
            if (temperature > 90) return SystemHealthStatus.Critical;
            if (temperature > 80) return SystemHealthStatus.Warning;
            return SystemHealthStatus.Normal;
        }

        private SystemHealthStatus GetOverallStatus(SystemHealthStatus cpu, SystemHealthStatus memory, SystemHealthStatus temp)
        {
            if (cpu == SystemHealthStatus.Critical || memory == SystemHealthStatus.Critical || temp == SystemHealthStatus.Critical)
                return SystemHealthStatus.Critical;
            
            if (cpu == SystemHealthStatus.Warning || memory == SystemHealthStatus.Warning || temp == SystemHealthStatus.Warning)
                return SystemHealthStatus.Warning;
            
            return SystemHealthStatus.Normal;
        }

        private SolidColorBrush GetStatusColor(SystemHealthStatus status)
        {
            return status switch
            {
                SystemHealthStatus.Normal => new SolidColorBrush(Color.FromArgb(255, 52, 168, 83)), // Green
                SystemHealthStatus.Warning => new SolidColorBrush(Color.FromArgb(255, 255, 193, 7)), // Yellow
                SystemHealthStatus.Critical => new SolidColorBrush(Color.FromArgb(255, 244, 67, 54)), // Red
                _ => new SolidColorBrush(Color.FromArgb(255, 169, 169, 169)) // Gray
            };
        }

        #endregion
    }

    #region Data Classes

    public class SystemStatusSummary
    {
        public bool IsHealthy { get; set; }
        public string Status { get; set; } = string.Empty;
        public double CpuUsage { get; set; }
        public double MemoryUsage { get; set; }
        public double Temperature { get; set; }
        public int ActiveProcesses { get; set; }
        public int AlertCount { get; set; }
        public SolidColorBrush StatusColor { get; set; } = new(Colors.Gray);
        public string CpuStatus { get; set; } = string.Empty;
        public string MemoryStatus { get; set; } = string.Empty;
        public string ThermalStatus { get; set; } = string.Empty;
    }

    public enum SystemHealthStatus
    {
        Normal,
        Warning,
        Critical
    }

    #endregion
}
