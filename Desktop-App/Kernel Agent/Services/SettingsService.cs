using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Windows.Storage;
using System.Collections.Generic;

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
        private Dictionary<string, object> _fallbackSettings = new();
        private bool _useApplicationData = true;
        private bool _storageInitialized = false;
        private readonly string _settingsFilePath;

        // Lazy initialization to avoid accessing ApplicationData too early
        private ApplicationDataContainer? LocalSettings
        {
            get
            {
                if (!_storageInitialized)
                {
                    _storageInitialized = true;
                    try
                    {
                        _localSettings = Windows.Storage.ApplicationData.Current.LocalSettings;
                        _useApplicationData = true;
                        System.Diagnostics.Debug.WriteLine("[SETTINGS] Using ApplicationData storage");
                    }
                    catch (Exception ex)
                    {
                        // Fallback: use JSON file storage for unpackaged apps
                        _useApplicationData = false;
                        System.Diagnostics.Debug.WriteLine($"[SETTINGS] ApplicationData not available, using JSON file storage: {ex.Message}");
                        LoadFromJsonFile();
                    }
                }
                return _localSettings;
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

        private const string KEY_SESSION_ID = "sessionId";

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
            // Use AppData folder for settings file
            var appDataPath = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var appFolder = System.IO.Path.Combine(appDataPath, "KernelAgent");
            System.IO.Directory.CreateDirectory(appFolder);
            _settingsFilePath = System.IO.Path.Combine(appFolder, "settings.json");
            
            System.Diagnostics.Debug.WriteLine($"[SETTINGS] Settings file: {_settingsFilePath}");
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

        public string SessionId
        {
            get
            {
                var existing = GetSetting(KEY_SESSION_ID, "");
                if (!string.IsNullOrWhiteSpace(existing))
                    return existing;

                var created = Guid.NewGuid().ToString();
                SetSetting(KEY_SESSION_ID, created);
                return created;
            }
            set
            {
                if (!string.IsNullOrWhiteSpace(value))
                    SetSetting(KEY_SESSION_ID, value);
            }
        }

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
                if (_useApplicationData)
                {
                    if (LocalSettings?.Values != null && LocalSettings.Values.TryGetValue(key, out var value))
                    {
                        return (T)value;
                    }
                }
                else
                {
                    // Use fallback dictionary
                    if (_fallbackSettings.TryGetValue(key, out var value))
                    {
                        return (T)value;
                    }
                }
            }
            catch { }
            return defaultValue;
        }

        private void SetSetting<T>(string key, T value)
        {
            try
            {
                if (_useApplicationData)
                {
                    if (LocalSettings?.Values != null)
                        LocalSettings.Values[key] = value;
                }
                else
                {
                    // Use fallback dictionary
                    _fallbackSettings[key] = value!;
                    SaveToJsonFile();
                }
                OnSettingChanged?.Invoke(key, value);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SETTINGS] SetSetting error: {ex.Message}");
            }
        }

        private void LoadFromJsonFile()
        {
            try
            {
                if (System.IO.File.Exists(_settingsFilePath))
                {
                    var json = System.IO.File.ReadAllText(_settingsFilePath);
                    var settings = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(json);
                    
                    if (settings != null)
                    {
                        _fallbackSettings = new Dictionary<string, object>();
                        foreach (var kvp in settings)
                        {
                            // Convert JsonElement to appropriate type
                            if (kvp.Value.ValueKind == JsonValueKind.String)
                                _fallbackSettings[kvp.Key] = kvp.Value.GetString()!;
                            else if (kvp.Value.ValueKind == JsonValueKind.True || kvp.Value.ValueKind == JsonValueKind.False)
                                _fallbackSettings[kvp.Key] = kvp.Value.GetBoolean();
                            else if (kvp.Value.ValueKind == JsonValueKind.Number)
                                _fallbackSettings[kvp.Key] = kvp.Value.GetInt32();
                        }
                        System.Diagnostics.Debug.WriteLine($"[SETTINGS] Loaded {_fallbackSettings.Count} settings from JSON file");
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SETTINGS] LoadFromJsonFile error: {ex.Message}");
            }
        }

        private void SaveToJsonFile()
        {
            try
            {
                var json = JsonSerializer.Serialize(_fallbackSettings, new JsonSerializerOptions
                {
                    WriteIndented = true
                });
                System.IO.File.WriteAllText(_settingsFilePath, json);
                System.Diagnostics.Debug.WriteLine("[SETTINGS] Saved settings to JSON file");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SETTINGS] SaveToJsonFile error: {ex.Message}");
            }
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
