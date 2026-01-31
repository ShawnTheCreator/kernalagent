using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Windows.Storage;
using Microsoft.UI.Xaml.Media;
using Windows.UI;
using Kernel_Agent.DTOs;

namespace Kernel_Agent.Services
{
    public class ApiService
    {
        private static readonly string API_BASE_URL = 
            (Environment.GetEnvironmentVariable("API_BASE_URL") ?? "https://kernal-agent-backend.onrender.com/api").TrimEnd('/') + "/";
        
        // Development: localhost, Production: kernalagent.onrender.com
        private static readonly string BASE_URL = "http://localhost:8000/";
        private static HttpClient? _httpClient;
        private static HttpClient? _kernelHttpClient;
        private static ApiService? _instance;
        
        // Persistent session ID for memory continuity (stored via SettingsService)
        private static string? _persistentSessionId;

        public static ApiService Instance
        {
            get
            {
                if (_instance == null)
                {
                    _instance = new ApiService();
                }
                return _instance;
            }
        }

        private ApiService()
        {
            _httpClient = new HttpClient
            {
                BaseAddress = new Uri(API_BASE_URL),
                Timeout = TimeSpan.FromSeconds(30)
            };
            _httpClient.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

            _kernelHttpClient = new HttpClient
            {
                BaseAddress = new Uri(BASE_URL),
                Timeout = TimeSpan.FromSeconds(60)
            };
            _kernelHttpClient.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

            try
            {
                _persistentSessionId = SettingsService.Instance.SessionId;
            }
            catch
            {
                _persistentSessionId ??= Guid.NewGuid().ToString();
            }

            System.Diagnostics.Debug.WriteLine($"[API_SERVICE] Using persistent session_id: {_persistentSessionId}");
        }

        private async Task<string?> PostKernelJsonWithRetryAsync(string relativeUrl, string primaryJson, string? fallbackJson, int timeoutSeconds, int maxRetries)
        {
            if (_kernelHttpClient == null)
            {
                return null;
            }

            Exception? lastEx = null;

            for (var attempt = 0; attempt <= maxRetries; attempt++)
            {
                var useFallback = attempt > 0 && !string.IsNullOrWhiteSpace(fallbackJson);
                var jsonToSend = useFallback ? (fallbackJson ?? primaryJson) : primaryJson;

                try
                {
                    using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(timeoutSeconds));
                    using var content = new StringContent(jsonToSend, Encoding.UTF8, "application/json");

                    var response = await _kernelHttpClient.PostAsync(relativeUrl, content, cts.Token);
                    if (!response.IsSuccessStatusCode)
                    {
                        var err = await response.Content.ReadAsStringAsync();
                        System.Diagnostics.Debug.WriteLine($"[KERNEL] {relativeUrl} failed: {(int)response.StatusCode} {response.ReasonPhrase} :: {err}");

                        if (attempt < maxRetries)
                        {
                            await Task.Delay(250 * (attempt + 1));
                            continue;
                        }

                        return null;
                    }

                    return await response.Content.ReadAsStringAsync();
                }
                catch (TaskCanceledException ex)
                {
                    lastEx = ex;
                    System.Diagnostics.Debug.WriteLine($"[KERNEL] {relativeUrl} timeout/canceled (attempt {attempt + 1}/{maxRetries + 1}): {ex.Message}");
                }
                catch (HttpRequestException ex)
                {
                    lastEx = ex;
                    System.Diagnostics.Debug.WriteLine($"[KERNEL] {relativeUrl} http error (attempt {attempt + 1}/{maxRetries + 1}): {ex.Message}");
                }
                catch (Exception ex)
                {
                    lastEx = ex;
                    System.Diagnostics.Debug.WriteLine($"[KERNEL] {relativeUrl} exception (attempt {attempt + 1}/{maxRetries + 1}): {ex.Message}");
                }

                if (attempt < maxRetries)
                {
                    await Task.Delay(250 * (attempt + 1));
                }
            }

            if (lastEx != null)
            {
                System.Diagnostics.Debug.WriteLine($"[KERNEL] {relativeUrl} final failure: {lastEx.Message}");
            }

            return null;
        }
        // Thread-safe in-memory token cache (ApplicationData throws from background threads)
        private static string? _cachedAuthToken = null;
        private static readonly object _tokenLock = new object();

        private async Task<string?> GetAuthTokenAsync()
        {
            try
            {
                // First check in-memory cache (thread-safe)
                lock (_tokenLock)
                {
                    if (!string.IsNullOrEmpty(_cachedAuthToken))
                    {
                        System.Diagnostics.Debug.WriteLine($"[API] GetAuthToken - From cache, Length: {_cachedAuthToken.Length}");
                        return _cachedAuthToken;
                    }
                }
                
                // Try to load from LocalSettings (may fail from background thread)
                try
                {
                    var localSettings = ApplicationData.Current.LocalSettings;
                    var token = localSettings.Values["AuthToken"] as string;
                    if (!string.IsNullOrEmpty(token))
                    {
                        lock (_tokenLock) { _cachedAuthToken = token; }
                        System.Diagnostics.Debug.WriteLine($"[API] GetAuthToken - From LocalSettings, Length: {token.Length}");
                        return token;
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[API] GetAuthToken - LocalSettings access failed: {ex.Message}");
                }
                
                System.Diagnostics.Debug.WriteLine("[API] GetAuthToken - No token found");
                return null;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] GetAuthToken ERROR: {ex.Message}");
                return null;
            }
        }

        public async Task SetAuthTokenAsync(string token)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"[API] SetAuthToken - Saving token of length: {token?.Length ?? 0}");
                
                // Always save to in-memory cache first (thread-safe)
                lock (_tokenLock)
                {
                    _cachedAuthToken = token;
                }
                System.Diagnostics.Debug.WriteLine("[API] SetAuthToken - Saved to in-memory cache ✓");
                
                // Try to persist to LocalSettings (may fail from background thread)
                try
                {
                    var localSettings = ApplicationData.Current.LocalSettings;
                    localSettings.Values["AuthToken"] = token;
                    System.Diagnostics.Debug.WriteLine("[API] SetAuthToken - Persisted to LocalSettings ✓");
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[API] SetAuthToken - LocalSettings persist failed (will retry on UI thread): {ex.Message}");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] SetAuthToken ERROR: {ex.Message}");
            }
        }

        private async Task ClearAuthTokenAsync()
        {
            try
            {
                lock (_tokenLock) { _cachedAuthToken = null; }
                
                try
                {
                    var localSettings = ApplicationData.Current.LocalSettings;
                    localSettings.Values.Remove("AuthToken");
                }
                catch { }
            }
            catch { }
        }

        public async Task<bool> LoginAsync(string email, string password)
        {
            try
            {
                var request = new
                {
                    email,
                    password
                };

                var json = JsonSerializer.Serialize(request);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await _httpClient!.PostAsync("auth/login", content);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync();
                    var authResponse = JsonSerializer.Deserialize<AuthResponse>(responseJson, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });

                    if (authResponse != null && !string.IsNullOrEmpty(authResponse.Token))
                    {
                        await SetAuthTokenAsync(authResponse.Token);
                        return true;
                    }
                }

                return false;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Login error: {ex.Message}");
                return false;
            }
        }

        public async Task<bool> SignupAsync(string name, string email, string password)
        {
            try
            {
                var request = new
                {
                    name,
                    email,
                    password
                };

                var json = JsonSerializer.Serialize(request);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await _httpClient!.PostAsync("auth/signup", content);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync();
                    var authResponse = JsonSerializer.Deserialize<AuthResponse>(responseJson, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });

                    if (authResponse != null && !string.IsNullOrEmpty(authResponse.Token))
                    {
                        await SetAuthTokenAsync(authResponse.Token);
                        return true;
                    }
                }

                    return false;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Signup error: {ex.Message}");
                return false;
            }
        }

        public async Task<bool> IsAuthenticatedAsync()
        {
            var token = await GetAuthTokenAsync();
            var isAuth = !string.IsNullOrEmpty(token);
            System.Diagnostics.Debug.WriteLine($"[API] IsAuthenticatedAsync - Result: {isAuth}");
            return isAuth;
        }

        public async Task LogoutAsync()
        {
            await ClearAuthTokenAsync();
        }

        public async Task<UserDto?> GetCurrentUserAsync()
        {
            try
            {
                var token = await GetAuthTokenAsync();
                if (string.IsNullOrEmpty(token))
                {
                    System.Diagnostics.Debug.WriteLine("[API] GetCurrentUser - No auth token");
                    return null;
                }

                // Call local Python microservice for user profile
                using var client = new HttpClient();
                client.DefaultRequestHeaders.Authorization = 
                    new AuthenticationHeaderValue("Bearer", token);

                var url = $"{MICROSERVICE_URL}/me";
                System.Diagnostics.Debug.WriteLine($"[API] GetCurrentUser - Calling: {url}");
                
                var response = await client.GetAsync(url);
                System.Diagnostics.Debug.WriteLine($"[API] GetCurrentUser - Status: {response.StatusCode}");
                
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[API] GetCurrentUser - Response: {json.Substring(0, Math.Min(200, json.Length))}...");
                    
                    // Parse the response - microservice returns UserProfileResponse
                    using var doc = System.Text.Json.JsonDocument.Parse(json);
                    var root = doc.RootElement;

                    string? photoUrl = null;
                    if (root.TryGetProperty("photoURL", out var photoEl))
                        photoUrl = photoEl.GetString();
                    else if (root.TryGetProperty("photoUrl", out var photoEl2))
                        photoUrl = photoEl2.GetString();
                    else if (root.TryGetProperty("photo_url", out var photoEl3))
                        photoUrl = photoEl3.GetString();
                    else if (root.TryGetProperty("picture", out var photoEl4))
                        photoUrl = photoEl4.GetString();
                    
                    var user = new UserDto
                    {
                        UserId = root.TryGetProperty("id", out var idEl) ? idEl.GetString() : null,
                        Name = root.TryGetProperty("name", out var nameEl) ? nameEl.GetString() ?? "User" : "User",
                        Email = root.TryGetProperty("email", out var emailEl) ? emailEl.GetString() : null,
                        PhotoUrl = photoUrl,
                    };
                    
                    // Parse createdAt if present
                    if (root.TryGetProperty("createdAt", out var createdEl))
                    {
                        var createdStr = createdEl.GetString();
                        if (!string.IsNullOrEmpty(createdStr) && DateTime.TryParse(createdStr, out var createdAt))
                        {
                            user.CreatedAt = createdAt;
                        }
                    }
                    
                    System.Diagnostics.Debug.WriteLine($"[API] GetCurrentUser - Parsed: {user.Name}, {user.Email}");
                    return user;
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[API] GetCurrentUser - Error: {errorContent}");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] GetCurrentUser error: {ex.Message}");
            }
            
            return null;
        }

        public async Task<string?> AskAgentAsync(string message)
        {
            var data = new { Message = message };
            // This endpoint likely sits on the python microservice or routed via dashboard?
            // "The App sends an HTTPS POST request... It includes your Firebase ID Token... Forwarding: It then sends..."
            // "The C# Backend receives the command first." 
            // I added `agent/command` in SendCommandAsync.
            // This `ask-agent` seems legacy? Leaving it but fixing slash.
            var response = await PostAsync<string>("ask-agent", data);
            return response;
        }

        public async Task<T?> GetAsync<T>(string endpoint)
        {
            try
            {
                var token = await GetAuthTokenAsync();
                if (!string.IsNullOrEmpty(token))
                {
                    _httpClient!.DefaultRequestHeaders.Authorization = 
                        new AuthenticationHeaderValue("Bearer", token);
                }

                var response = await _httpClient!.GetAsync(endpoint);
                
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    return JsonSerializer.Deserialize<T>(json, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                }

                return default(T);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"GET error: {ex.Message}");
                return default(T);
            }
        }

        public async Task<T?> PostAsync<T>(string endpoint, object data)
        {
            try
            {
                var token = await GetAuthTokenAsync();
                if (!string.IsNullOrEmpty(token))
                {
                    _httpClient!.DefaultRequestHeaders.Authorization = 
                        new AuthenticationHeaderValue("Bearer", token);
                }

                var json = JsonSerializer.Serialize(data);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await _httpClient!.PostAsync(endpoint, content);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync();
                    return JsonSerializer.Deserialize<T>(responseJson, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                }

                return default(T);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"POST error: {ex.Message}");
                return default(T);
            }
        }
        public async Task<bool> CheckLoginStatusAsync(string deviceId)
        {
            try
            {
                // OPTIMIZATION: Try local Python microservice FIRST (fast, no network delay)
                // This syncs instantly when user logs in via web
                try
                {
                    var localUrl = $"{MICROSERVICE_URL}/api/auth/poll?deviceId={deviceId}";
                    using var localClient = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
                    var localResponse = await localClient.GetAsync(localUrl);
                    
                    if (localResponse.IsSuccessStatusCode)
                    {
                        var localJson = await localResponse.Content.ReadAsStringAsync();
                        using var localDoc = System.Text.Json.JsonDocument.Parse(localJson);
                        
                        if (localDoc.RootElement.TryGetProperty("token", out var tokenEl))
                        {
                            var token = tokenEl.GetString();
                            if (!string.IsNullOrEmpty(token))
                            {
                                System.Diagnostics.Debug.WriteLine("[API] ⚡ LOCAL auth succeeded (fast path)!");
                                await SetAuthTokenAsync(token);
                                return true;
                            }
                        }
                    }
                }
                catch (Exception localEx)
                {
                    System.Diagnostics.Debug.WriteLine($"[API] Local poll failed, trying remote: {localEx.Message}");
                }
                
                // FALLBACK: Remote Render server (slower, but works if local isn't running)
                var url = $"auth/poll?deviceId={deviceId}";
                var response = await _httpClient!.GetAsync(url);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync();
                    var authResponse = JsonSerializer.Deserialize<AuthResponse>(responseJson, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });

                    if (authResponse != null && !string.IsNullOrEmpty(authResponse.Token))
                    {
                        System.Diagnostics.Debug.WriteLine("[API] Token received from remote!");
                        await SetAuthTokenAsync(authResponse.Token);
                        return true;
                    }
                }
                else if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
                {
                    // 404 = still waiting for login
                    return false;
                }
                
                return false;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] Poll error: {ex.Message}");
                return false;
            }
        }

        public async Task<string?> SendCommandAsync(string commandText)
        {
            try
            {
                return await GetPlanV2RawAsync(commandText);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[COMMAND] Error: {ex.Message}");
                return null;
            }
        }

        public async Task<string?> GetPlanV2RawAsync(string commandText)
        {
            try
            {
                // ========================================
                // Call Python Brain backend (LLM-First v2)
                // Returns plan JSON ONLY. Execution must be done by Kernel/SmartExecutor.
                // ========================================
                var pythonBackendUrl = "http://localhost:8000/api/agent/plan/v2";

                using var client = new HttpClient();
                client.Timeout = TimeSpan.FromSeconds(30);

                if (string.IsNullOrWhiteSpace(_persistentSessionId))
                {
                    try
                    {
                        _persistentSessionId = SettingsService.Instance.SessionId;
                    }
                    catch
                    {
                        _persistentSessionId = Guid.NewGuid().ToString();
                    }
                }

                Dictionary<string, object>? contextPayload = null;
                try
                {
                    var contextManager = ContextManager.Instance;
                    contextManager.RefreshContext();
                    contextPayload = contextManager.GetContextDict();
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[CONTEXT] Failed to build context payload: {ex.Message}");
                }

                var requestBody = new { command = commandText, session_id = _persistentSessionId, context = contextPayload };
                var json = JsonSerializer.Serialize(requestBody);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                System.Diagnostics.Debug.WriteLine($"[COMMAND] Sending to Python: {commandText}");

                var response = await client.PostAsync(pythonBackendUrl, content);

                if (!response.IsSuccessStatusCode)
                {
                    System.Diagnostics.Debug.WriteLine($"[COMMAND] Error: {response.StatusCode}");
                    return null;
                }

                var responseJson = await response.Content.ReadAsStringAsync();
                System.Diagnostics.Debug.WriteLine($"[COMMAND] Full Response JSON: {responseJson}");
                return responseJson;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[COMMAND] GetPlanV2RawAsync error: {ex.Message}");
                return null;
            }
        }

        public async Task<string?> GetKernelInterpretationRawAsync(string commandText)
        {
            try
            {
                Dictionary<string, object>? contextPayload = null;
                try
                {
                    var contextManager = ContextManager.Instance;
                    contextManager.RefreshContext();
                    contextPayload = contextManager.GetContextDict();
                }
                catch
                {
                }

                string primaryJson;
                string? fallbackJson = null;

                try
                {
                    var requestBody = new { command = commandText, session_id = _persistentSessionId, context = contextPayload };
                    primaryJson = JsonSerializer.Serialize(requestBody);
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[KERNEL] Interpret serialize failed (with context): {ex.Message}");
                    var requestBody = new { command = commandText, session_id = _persistentSessionId, context = (object?)null };
                    primaryJson = JsonSerializer.Serialize(requestBody);
                }

                if (contextPayload != null)
                {
                    try
                    {
                        var requestBodyFallback = new { command = commandText, session_id = _persistentSessionId, context = (object?)null };
                        fallbackJson = JsonSerializer.Serialize(requestBodyFallback);
                    }
                    catch
                    {
                        fallbackJson = null;
                    }
                }

                return await PostKernelJsonWithRetryAsync("api/kernel/interpret", primaryJson, fallbackJson, timeoutSeconds: 15, maxRetries: 2);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[KERNEL] Interpret exception: {ex.Message}");
                return null;
            }
        }

        public async Task<string?> GetKernelPlanRawAsync(string commandText, string interpretationJson)
        {
            try
            {
                Dictionary<string, object>? contextPayload = null;
                try
                {
                    var contextManager = ContextManager.Instance;
                    contextManager.RefreshContext();
                    contextPayload = contextManager.GetContextDict();
                }
                catch
                {
                }

                JsonElement interpEl;
                try
                {
                    interpEl = JsonSerializer.Deserialize<JsonElement>(interpretationJson);
                }
                catch
                {
                    interpEl = new JsonElement();
                }

                string primaryJson;
                string? fallbackJson = null;

                try
                {
                    var requestBody = new { command = commandText, interpretation = interpEl, session_id = _persistentSessionId, context = contextPayload };
                    primaryJson = JsonSerializer.Serialize(requestBody);
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[KERNEL] Plan serialize failed (with context): {ex.Message}");
                    var requestBody = new { command = commandText, interpretation = interpEl, session_id = _persistentSessionId, context = (object?)null };
                    primaryJson = JsonSerializer.Serialize(requestBody);
                }

                if (contextPayload != null)
                {
                    try
                    {
                        var requestBodyFallback = new { command = commandText, interpretation = interpEl, session_id = _persistentSessionId, context = (object?)null };
                        fallbackJson = JsonSerializer.Serialize(requestBodyFallback);
                    }
                    catch
                    {
                        fallbackJson = null;
                    }
                }

                return await PostKernelJsonWithRetryAsync("api/kernel/plan", primaryJson, fallbackJson, timeoutSeconds: 30, maxRetries: 2);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[KERNEL] Plan exception: {ex.Message}");
                return null;
            }
        }

        // =====================================================
        // NEW: Python Microservice Endpoints for Real Data
        // =====================================================
        private static readonly string MICROSERVICE_URL = 
            Environment.GetEnvironmentVariable("MICROSERVICE_URL") ?? "http://localhost:8000";

        public async Task<List<SkillDto>> GetMySkillsAsync()
        {
            try
            {
                var token = await GetAuthTokenAsync();
                System.Diagnostics.Debug.WriteLine($"[API] GetMySkills - Token present: {!string.IsNullOrEmpty(token)}");
                
                if (string.IsNullOrEmpty(token))
                {
                    System.Diagnostics.Debug.WriteLine("[API] GetMySkills - No auth token, returning empty");
                    return new List<SkillDto>();
                }

                using var client = new HttpClient();
                client.DefaultRequestHeaders.Authorization = 
                    new AuthenticationHeaderValue("Bearer", token);

                var url = $"{MICROSERVICE_URL}/me/skills";
                System.Diagnostics.Debug.WriteLine($"[API] GetMySkills - Calling: {url}");
                
                var response = await client.GetAsync(url);
                System.Diagnostics.Debug.WriteLine($"[API] GetMySkills - Status: {response.StatusCode}");
                
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[API] GetMySkills - Response: {json.Substring(0, Math.Min(200, json.Length))}...");
                    
                    var skills = JsonSerializer.Deserialize<List<SkillDto>>(json, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                    System.Diagnostics.Debug.WriteLine($"[API] GetMySkills - Parsed {skills?.Count ?? 0} skills");
                    return skills ?? new List<SkillDto>();
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[API] GetMySkills - Error response: {errorContent}");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] GetMySkills error: {ex.Message}");
                System.Diagnostics.Debug.WriteLine($"[API] GetMySkills stack: {ex.StackTrace}");
            }
            return new List<SkillDto>();
        }

        public async Task<string?> CreateSkillAsync(string name, string intentSignature, string description, double confidence = 0.9)
        {
            try
            {
                var token = await GetAuthTokenAsync();
                System.Diagnostics.Debug.WriteLine($"[API] CreateSkill - Token present: {!string.IsNullOrEmpty(token)}");
                
                if (string.IsNullOrEmpty(token))
                {
                    System.Diagnostics.Debug.WriteLine("[API] CreateSkill - No auth token");
                    return null;
                }

                using var client = new HttpClient();
                client.DefaultRequestHeaders.Authorization = 
                    new AuthenticationHeaderValue("Bearer", token);

                var skillData = new
                {
                    name,
                    intent_signature = intentSignature,
                    description,
                    confidence
                };

                var json = JsonSerializer.Serialize(skillData);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var url = $"{MICROSERVICE_URL}/me/skills";
                System.Diagnostics.Debug.WriteLine($"[API] CreateSkill - Calling: {url}");
                System.Diagnostics.Debug.WriteLine($"[API] CreateSkill - Data: {json}");
                
                var response = await client.PostAsync(url, content);
                System.Diagnostics.Debug.WriteLine($"[API] CreateSkill - Status: {response.StatusCode}");
                
                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[API] CreateSkill - Response: {responseJson}");
                    
                    // Parse response to get skill ID
                    var result = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(responseJson);
                    if (result != null && result.ContainsKey("skill_id"))
                    {
                        var skillId = result["skill_id"].GetString();
                        System.Diagnostics.Debug.WriteLine($"[API] CreateSkill - Success! Skill ID: {skillId}");
                        return skillId;
                    }
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[API] CreateSkill - Error: {errorContent}");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] CreateSkill error: {ex.Message}");
                System.Diagnostics.Debug.WriteLine($"[API] CreateSkill stack: {ex.StackTrace}");
            }
            return null;
        }

        public async Task<List<SessionDto>> GetMySessionsAsync()
        {
            try
            {
                var token = await GetAuthTokenAsync();
                if (string.IsNullOrEmpty(token)) return new List<SessionDto>();

                using var client = new HttpClient();
                client.DefaultRequestHeaders.Authorization = 
                    new AuthenticationHeaderValue("Bearer", token);

                var response = await client.GetAsync($"{MICROSERVICE_URL}/me/sessions");
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    var sessions = JsonSerializer.Deserialize<List<SessionDto>>(json, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                    return sessions ?? new List<SessionDto>();
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] GetMySessions error: {ex.Message}");
            }
            return new List<SessionDto>();
        }

        public async Task<MemoryDto?> GetMyMemoryAsync()
        {
            try
            {
                var token = await GetAuthTokenAsync();
                if (string.IsNullOrEmpty(token)) return null;

                using var client = new HttpClient();
                client.DefaultRequestHeaders.Authorization = 
                    new AuthenticationHeaderValue("Bearer", token);

                var response = await client.GetAsync($"{MICROSERVICE_URL}/me/memory");
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    return JsonSerializer.Deserialize<MemoryDto>(json, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] GetMyMemory error: {ex.Message}");
            }
            return null;
        }

        public async Task<DashboardStatsDto?> GetDashboardStatsAsync()
        {
            try
            {
                return await GetAsync<DashboardStatsDto>("dashboard/stats");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] GetDashboardStats error: {ex.Message}");
            }
            return null;
        }
        public async Task<TimelineResponse?> GetMemoryTimelineAsync(int limit = 50)
        {
            try
            {
                var token = await GetAuthTokenAsync();
                if (string.IsNullOrEmpty(token)) return null;

                using var client = new HttpClient();
                client.DefaultRequestHeaders.Authorization = 
                    new AuthenticationHeaderValue("Bearer", token);

                // FIXED: Adjusted path to match router prefix (/api/agents)
                var response = await client.GetAsync($"{MICROSERVICE_URL}/api/agents/memory/timeline?limit={limit}");
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    return JsonSerializer.Deserialize<TimelineResponse>(json, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] GetMemoryTimeline error: {ex.Message}");
            }
            return null;
        }
        public async Task<bool> LogTimelineEventAsync(string type, string content, Dictionary<string, object>? metadata = null)
        {
            try
            {
                var token = await GetAuthTokenAsync();
                
                // Construct payload
                var data = new
                {
                    type,
                    content,
                    metadata = metadata ?? new Dictionary<string, object>()
                };

                using var client = new HttpClient();
                if (!string.IsNullOrEmpty(token))
                {
                    client.DefaultRequestHeaders.Authorization = 
                        new AuthenticationHeaderValue("Bearer", token);
                }

                var json = JsonSerializer.Serialize(data);
                var httpContent = new StringContent(json, Encoding.UTF8, "application/json");

                System.Diagnostics.Debug.WriteLine($"[API] Logging event: {content}");
                var response = await client.PostAsync($"{MICROSERVICE_URL}/api/agents/memory/timeline", httpContent);
                return response.IsSuccessStatusCode;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] LogTimelineEvent error: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Generate speech from text using Google Cloud Text-to-Speech API
        /// </summary>
        public async Task<byte[]> GenerateSpeechAsync(string text)
        {
            try
            {
                if (string.IsNullOrEmpty(text))
                {
                    System.Diagnostics.Debug.WriteLine("[TTS] No text provided for speech generation");
                    return Array.Empty<byte>();
                }

                System.Diagnostics.Debug.WriteLine($"[TTS] Requesting speech for: {text.Substring(0, Math.Min(50, text.Length))}...");

                var payload = new
                {
                    text,
                    voice = "en-US-GuyNeural",
                    rate = "+0%",
                    volume = "+0%",
                    pitch = "+0Hz"
                };

                using var client = new HttpClient
                {
                    Timeout = TimeSpan.FromSeconds(30)
                };

                var json = JsonSerializer.Serialize(payload);
                using var httpContent = new StringContent(json, Encoding.UTF8, "application/json");

                // Edge TTS microservice endpoint returns streaming MP3 (audio/mpeg)
                using var response = await client.PostAsync($"{MICROSERVICE_URL}/api/tts/speak", httpContent);
                if (!response.IsSuccessStatusCode)
                {
                    var err = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[TTS] TTS request failed: {(int)response.StatusCode} {response.ReasonPhrase} :: {err}");
                    return Array.Empty<byte>();
                }

                var audioBytes = await response.Content.ReadAsByteArrayAsync();
                System.Diagnostics.Debug.WriteLine($"[TTS] Received {audioBytes.Length} bytes of audio");
                return audioBytes;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[TTS] Speech generation error: {ex.Message}");
                return Array.Empty<byte>();
            }
        }

        // Memory API methods
        public async Task<string> GetMemoryPatternsAsync(string? intent = null, double minSuccessRate = 0.7, int minUsageCount = 2, int limit = 10)
        {
            try
            {
                var queryParams = new List<string>();
                if (!string.IsNullOrEmpty(intent))
                    queryParams.Add($"intent={Uri.EscapeDataString(intent)}");
                queryParams.Add($"min_success_rate={minSuccessRate}");
                queryParams.Add($"min_usage_count={minUsageCount}");
                queryParams.Add($"limit={limit}");

                var url = $"{MICROSERVICE_URL}/api/memory/patterns";
                if (queryParams.Count > 0)
                    url += "?" + string.Join("&", queryParams);

                using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
                var response = await client.GetAsync(url);
                
                if (!response.IsSuccessStatusCode)
                {
                    var err = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[MEMORY] Failed to get patterns: {err}");
                    return "{}";
                }

                return await response.Content.ReadAsStringAsync();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[MEMORY] Error getting patterns: {ex.Message}");
                return "{}";
            }
        }

        public async Task<string> GetMemoryStatsAsync()
        {
            try
            {
                using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
                var response = await client.GetAsync($"{MICROSERVICE_URL}/api/memory/stats");
                
                if (!response.IsSuccessStatusCode)
                {
                    var err = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[MEMORY] Failed to get stats: {err}");
                    return "{}";
                }

                return await response.Content.ReadAsStringAsync();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[MEMORY] Error getting stats: {ex.Message}");
                return "{}";
            }
        }
    }

    public class AuthResponse
    {
        public string Token { get; set; } = string.Empty;
        public UserDto User { get; set; } = new UserDto();
    }

    public class UserDto
    {
        public int Id { get; set; }
        
        [System.Text.Json.Serialization.JsonPropertyName("user_id")]
        public string? UserId { get; set; }
        
        public string Name { get; set; } = string.Empty;
        public string Email { get; set; } = string.Empty;
        
        [System.Text.Json.Serialization.JsonPropertyName("photo_url")]
        public string? PhotoUrl { get; set; }
        
        [System.Text.Json.Serialization.JsonPropertyName("created_at")]
        public DateTime? CreatedAt { get; set; }
    }
}
