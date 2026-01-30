using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Timers;
using Kernel_Agent.DTOs;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Enhanced Data Service - Pulls all necessary data from backend
    /// Provides real-time updates for Dashboard, Skills, Activities, and Metrics
    /// </summary>
    public class DataSyncService
    {
        private static DataSyncService? _instance;
        public static DataSyncService Instance => _instance ??= new DataSyncService();

        private Timer? _syncTimer;
        private const int SYNC_INTERVAL_MS = 5000; // Sync every 5 seconds

        // Cached data
        public List<SkillDto>? Skills { get; private set; }
        public List<ActivityDto>? Activities { get; private set; }
        public MetricsDto? Metrics { get; private set; }
        public DashboardStatsDto? Stats { get; private set; }
        public List<SessionDto>? Sessions { get; private set; }
        public List<MemoryDto>? Memories { get; private set; }

        // Events for real-time UI updates
        public event Action<List<SkillDto>>? OnSkillsUpdated;
        public event Action<List<ActivityDto>>? OnActivitiesUpdated;
        public event Action<MetricsDto>? OnMetricsUpdated;
        public event Action<DashboardStatsDto>? OnStatsUpdated;
        public event Action<List<SessionDto>>? OnSessionsUpdated;
        public event Action<List<MemoryDto>>? OnMemoriesUpdated;
        public event Action<string>? OnError;

        private bool _isRunning = false;

        private DataSyncService()
        {
            // Private constructor for singleton
        }

        /// <summary>
        /// Start automatic data synchronization
        /// </summary>
        public void StartSync()
        {
            if (_isRunning) return;

            _isRunning = true;
            System.Diagnostics.Debug.WriteLine("[DataSync] Starting automatic sync...");

            // Initial sync
            _ = SyncAllDataAsync();

            // Setup timer for periodic sync
            _syncTimer = new Timer(SYNC_INTERVAL_MS);
            _syncTimer.Elapsed += async (sender, e) => await SyncAllDataAsync();
            _syncTimer.AutoReset = true;
            _syncTimer.Start();

            System.Diagnostics.Debug.WriteLine("[DataSync] Automatic sync started");
        }

        /// <summary>
        /// Stop automatic data synchronization
        /// </summary>
        public void StopSync()
        {
            if (!_isRunning) return;

            _syncTimer?.Stop();
            _syncTimer?.Dispose();
            _syncTimer = null;
            _isRunning = false;

            System.Diagnostics.Debug.WriteLine("[DataSync] Automatic sync stopped");
        }

        /// <summary>
        /// Manually trigger a full data sync
        /// </summary>
        public async Task SyncAllDataAsync()
        {
            try
            {
                System.Diagnostics.Debug.WriteLine("[DataSync] Syncing all data...");

                // Sync all data in parallel for better performance
                var tasks = new List<Task>
                {
                    SyncSkillsAsync(),
                    SyncActivitiesAsync(),
                    SyncMetricsAsync(),
                    SyncStatsAsync(),
                    SyncSessionsAsync(),
                    SyncMemoriesAsync()
                };

                await Task.WhenAll(tasks);

                System.Diagnostics.Debug.WriteLine("[DataSync] All data synced successfully");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[DataSync] Error syncing data: {ex.Message}");
                OnError?.Invoke($"Data sync failed: {ex.Message}");
            }
        }

        /// <summary>
        /// Sync skills from backend
        /// </summary>
        public async Task SyncSkillsAsync()
        {
            try
            {
                var skills = await ApiService.Instance.GetMySkillsAsync();
                if (skills != null && skills.Any())
                {
                    Skills = skills.ToList();
                    OnSkillsUpdated?.Invoke(Skills);
                    System.Diagnostics.Debug.WriteLine($"[DataSync] Synced {Skills.Count} skills");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[DataSync] Error syncing skills: {ex.Message}");
            }
        }

        /// <summary>
        /// Sync activities from backend
        /// </summary>
        public async Task SyncActivitiesAsync()
        {
            try
            {
                // Call the dashboard activities endpoint
                var response = await ApiService.Instance.GetAsync<string>("dashboard/activities");
                if (response != null)
                {
                    var activities = System.Text.Json.JsonSerializer.Deserialize<List<ActivityDto>>(
                        response,
                        new System.Text.Json.JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                    );

                    if (activities != null && activities.Any())
                    {
                        Activities = activities;
                        OnActivitiesUpdated?.Invoke(Activities);
                        System.Diagnostics.Debug.WriteLine($"[DataSync] Synced {Activities.Count} activities");
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[DataSync] Error syncing activities: {ex.Message}");
            }
        }

        /// <summary>
        /// Sync metrics from backend
        /// </summary>
        public async Task SyncMetricsAsync()
        {
            try
            {
                var response = await ApiService.Instance.GetAsync<string>("dashboard/metrics");
                if (response != null)
                {
                    var metrics = System.Text.Json.JsonSerializer.Deserialize<MetricsDto>(
                        response,
                        new System.Text.Json.JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                    );

                    if (metrics != null)
                    {
                        Metrics = metrics;
                        OnMetricsUpdated?.Invoke(Metrics);
                        System.Diagnostics.Debug.WriteLine("[DataSync] Synced metrics");
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[DataSync] Error syncing metrics: {ex.Message}");
            }
        }

        /// <summary>
        /// Sync dashboard stats from backend
        /// </summary>
        public async Task SyncStatsAsync()
        {
            try
            {
                var stats = await ApiService.Instance.GetDashboardStatsAsync();
                if (stats != null)
                {
                    Stats = stats;
                    OnStatsUpdated?.Invoke(Stats);
                    System.Diagnostics.Debug.WriteLine("[DataSync] Synced dashboard stats");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[DataSync] Error syncing stats: {ex.Message}");
            }
        }

        /// <summary>
        /// Sync sessions from backend
        /// </summary>
        public async Task SyncSessionsAsync()
        {
            try
            {
                var sessions = await ApiService.Instance.GetMySessionsAsync();
                if (sessions != null && sessions.Any())
                {
                    Sessions = sessions.ToList();
                    OnSessionsUpdated?.Invoke(Sessions);
                    System.Diagnostics.Debug.WriteLine($"[DataSync] Synced {Sessions.Count} sessions");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[DataSync] Error syncing sessions: {ex.Message}");
            }
        }

        /// <summary>
        /// Sync memories from backend
        /// </summary>
        public async Task SyncMemoriesAsync()
        {
            try
            {
                var memories = await ApiService.Instance.GetMyMemoryAsync();
                if (memories != null && memories.FrequentSkills != null && memories.FrequentSkills.Any())
                {
                    Memories = new List<MemoryDto> { memories };
                    OnMemoriesUpdated?.Invoke(Memories);
                    System.Diagnostics.Debug.WriteLine($"[DataSync] Synced {Memories.Count} memories");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[DataSync] Error syncing memories: {ex.Message}");
            }
        }

        /// <summary>
        /// Get cached skills or fetch if not available
        /// </summary>
        public async Task<List<SkillDto>> GetSkillsAsync()
        {
            if (Skills == null || !Skills.Any())
            {
                await SyncSkillsAsync();
            }
            return Skills ?? new List<SkillDto>();
        }

        /// <summary>
        /// Get cached activities or fetch if not available
        /// </summary>
        public async Task<List<ActivityDto>> GetActivitiesAsync()
        {
            if (Activities == null || !Activities.Any())
            {
                await SyncActivitiesAsync();
            }
            return Activities ?? new List<ActivityDto>();
        }

        /// <summary>
        /// Get cached metrics or fetch if not available
        /// </summary>
        public async Task<MetricsDto?> GetMetricsAsync()
        {
            if (Metrics == null)
            {
                await SyncMetricsAsync();
            }
            return Metrics;
        }

        /// <summary>
        /// Get cached stats or fetch if not available
        /// </summary>
        public async Task<DashboardStatsDto?> GetStatsAsync()
        {
            if (Stats == null)
            {
                await SyncStatsAsync();
            }
            return Stats;
        }
    }
}
