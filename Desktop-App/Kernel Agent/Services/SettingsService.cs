using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Windows.Storage;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Settings service that syncs with Python microservice /me/settings
    /// while maintaining local fallback storage.
    /// </summary>
    public class SettingsService
    {
        private static SettingsService? _instance;
        private static readonly object _lock = new();
        private ApplicationDataContainer? _localSettings;

        // Lazy initialization to avoid accessing ApplicationData too early
        private ApplicationDataContainer LocalSettings
        {
            get
            {
                if (_localSettings == null)
                {
                    try
                    {
                        _localSettings = Windows.Storage.ApplicationData.Current.LocalSettings;
                    }
                    catch
                    {
                        // Fallback: create in-memory storage if app data not available
                        System.Diagnostics.Debug.WriteLine("[SETTINGS] ApplicationData not available, using defaults");
                    }
                }
                return _localSettings!;
            }
        }

        // Backend sync - Python Microservice
        private static readonly string MICROSERVICE_URL = 
            Environment.GetEnvironmentVariable("MICROSERVICE_URL") ?? "http://localhost:8000";

        // Local storage keys
        private const string KEY_THEME = "theme";
        private const string KEY_EXECUTION_MODE = "executionMode";
        private const string KEY_CONFIRM_ACTIONS = "confirmActions";
        private const string KEY_LANGUAGE = "language";
        private const string KEY_NOTIFICATIONS = "notificationsEnabled";
        private const string KEY_AUTO_SAVE_SKILLS = "autoSaveSkills";
        
        // Voice settings (local only - not synced to backend)
        private const string KEY_VOICE_ENABLED = "voiceEnabled";
        private const string KEY_SILENCE_THRESHOLD = "silenceThreshold";
        private const string KEY_SILENCE_DURATION_MS = "silenceDurationMs";
        private const string KEY_MIN_SPEECH_DURATION_MS = "minSpeechDurationMs";
        private const string KEY_VOICE_LANGUAGE = "voiceLanguage";

        public static SettingsService Instance
        {
            get
            {
                if (_instance == null)
                {
                    lock (_lock)
                    {
                        _instance ??= new SettingsService();
                    }
                }
                return _instance;
            }
        }

        private SettingsService()
        {
            // Defer LocalSettings initialization to first use
        }

        #region Backend-Synced Settings (Python Microservice)

        public string Theme
        {
            get => GetSetting(KEY_THEME, "dark");
            set => SetSetting(KEY_THEME, value);
        }

        public string ExecutionMode
        {
            get => GetSetting(KEY_EXECUTION_MODE, "MOCK");
            set => SetSetting(KEY_EXECUTION_MODE, value);
        }

        public bool ConfirmActions
        {
            get => GetSetting(KEY_CONFIRM_ACTIONS, true);
            set => SetSetting(KEY_CONFIRM_ACTIONS, value);
        }

        public string Language
        {
            get => GetSetting(KEY_LANGUAGE, "en");
            set => SetSetting(KEY_LANGUAGE, value);
        }

        public bool NotificationsEnabled
        {
            get => GetSetting(KEY_NOTIFICATIONS, true);
            set => SetSetting(KEY_NOTIFICATIONS, value);
        }

        public bool AutoSaveSkills
        {
            get => GetSetting(KEY_AUTO_SAVE_SKILLS, true);
            set => SetSetting(KEY_AUTO_SAVE_SKILLS, value);
        }

        #endregion

        #region Local-Only Voice Settings

        public bool VoiceEnabled
        {
            get => GetSetting(KEY_VOICE_ENABLED, true);
            set => SetSetting(KEY_VOICE_ENABLED, value);
        }

        public int SilenceThreshold
        {
            get => GetSetting(KEY_SILENCE_THRESHOLD, 500);
            set => SetSetting(KEY_SILENCE_THRESHOLD, value);
        }

        public int SilenceDurationMs
        {
            get => GetSetting(KEY_SILENCE_DURATION_MS, 1500);
            set => SetSetting(KEY_SILENCE_DURATION_MS, value);
        }

        public int MinSpeechDurationMs
        {
            get => GetSetting(KEY_MIN_SPEECH_DURATION_MS, 500);
            set => SetSetting(KEY_MIN_SPEECH_DURATION_MS, value);
        }

        public string VoiceLanguage
        {
            get => GetSetting(KEY_VOICE_LANGUAGE, "en-US");
            set => SetSetting(KEY_VOICE_LANGUAGE, value);
        }

        #endregion

        #region Backend Sync Methods

        /// <summary>
        /// Load settings from backend /me/settings and cache locally.
        /// </summary>
        public async Task<bool> SyncFromBackendAsync()
        {
            try
            {
                var token = await GetAuthTokenAsync();
                if (string.IsNullOrEmpty(token)) return false;

                using var client = new HttpClient();
                client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
                
                var response = await client.GetAsync($"{MICROSERVICE_URL}/me/settings");
                if (!response.IsSuccessStatusCode) return false;

                var json = await response.Content.ReadAsStringAsync();
                var settings = JsonSerializer.Deserialize<BackendSettingsDto>(json, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });

                if (settings != null)
                {
                    Theme = settings.Theme ?? "dark";
                    ExecutionMode = settings.ExecutionMode ?? "MOCK";
                    ConfirmActions = settings.ConfirmActions;
                    Language = settings.Language ?? "en";
                    NotificationsEnabled = settings.NotificationsEnabled;
                    AutoSaveSkills = settings.AutoSaveSkills;
                    
                    System.Diagnostics.Debug.WriteLine("[SETTINGS] Synced from backend");
                    return true;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SETTINGS] Sync error: {ex.Message}");
            }
            return false;
        }

        /// <summary>
        /// Save current settings to backend /me/settings.
        /// </summary>
        public async Task<bool> SyncToBackendAsync()
        {
            try
            {
                var token = await GetAuthTokenAsync();
                if (string.IsNullOrEmpty(token)) return false;

                using var client = new HttpClient();
                client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);

                var settings = new BackendSettingsDto
                {
                    Theme = Theme,
                    ExecutionMode = ExecutionMode,
                    ConfirmActions = ConfirmActions,
                    Language = Language,
                    NotificationsEnabled = NotificationsEnabled,
                    AutoSaveSkills = AutoSaveSkills
                };

                var json = JsonSerializer.Serialize(settings);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                
                var response = await client.PatchAsync($"{MICROSERVICE_URL}/me/settings", content);
                
                if (response.IsSuccessStatusCode)
                {
                    System.Diagnostics.Debug.WriteLine("[SETTINGS] Saved to backend");
                    return true;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SETTINGS] Save error: {ex.Message}");
            }
            return false;
        }

        #endregion

        #region Helper Methods

        private async Task<string?> GetAuthTokenAsync()
        {
            try
            {
                if (LocalSettings?.Values == null) return null;
                return LocalSettings.Values["AuthToken"] as string;
            }
            catch
            {
                return null;
            }
        }

        private T GetSetting<T>(string key, T defaultValue)
        {
            try
            {
                if (LocalSettings?.Values != null && LocalSettings.Values.TryGetValue(key, out var value))
                {
                    return (T)value;
                }
            }
            catch { }
            return defaultValue;
        }

        private void SetSetting<T>(string key, T value)
        {
            try
            {
                if (LocalSettings?.Values != null)
                    LocalSettings.Values[key] = value;
                OnSettingChanged?.Invoke(key, value);
            }
            catch { }
        }

        public void ResetToDefaults()
        {
            Theme = "dark";
            ExecutionMode = "MOCK";
            ConfirmActions = true;
            Language = "en";
            NotificationsEnabled = true;
            AutoSaveSkills = true;
            VoiceEnabled = true;
            SilenceThreshold = 500;
            SilenceDurationMs = 1500;
            MinSpeechDurationMs = 500;
            VoiceLanguage = "en-US";
            
            OnSettingsReset?.Invoke();
        }

        #endregion

        #region Events

        public event Action<string, object?>? OnSettingChanged;
        public event Action? OnSettingsReset;

        #endregion
    }

    /// <summary>
    /// Backend settings DTO matching Python microservice schema.
    /// </summary>
    public class BackendSettingsDto
    {
        public string? Theme { get; set; } = "dark";
        public string? ExecutionMode { get; set; } = "MOCK";
        public bool ConfirmActions { get; set; } = true;
        public string? Language { get; set; } = "en";
        public bool NotificationsEnabled { get; set; } = true;
        public bool AutoSaveSkills { get; set; } = true;
    }
}
