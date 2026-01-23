using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Windows.Storage;

namespace Kernel_Agent.Services
{
    public class ApiService
    {
        private static readonly string API_BASE_URL = 
            (Environment.GetEnvironmentVariable("API_BASE_URL") ?? "https://kernal-agent-backend.onrender.com/api").TrimEnd('/') + "/";
        
        // Development: localhost, Production: kernalagent.onrender.com
        private static readonly string BASE_URL = "http://localhost:8000/";
        private static HttpClient? _httpClient;
        private static ApiService? _instance;

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
        }

        private async Task<string?> GetAuthTokenAsync()
        {
            try
            {
                var localSettings = ApplicationData.Current.LocalSettings;
                return localSettings.Values["AuthToken"] as string;
            }
            catch
            {
                return null;
            }
        }

        public async Task SetAuthTokenAsync(string token)
        {
            try
            {
                var localSettings = ApplicationData.Current.LocalSettings;
                localSettings.Values["AuthToken"] = token;
            }
            catch { }
        }

        private async Task ClearAuthTokenAsync()
        {
            try
            {
                var localSettings = ApplicationData.Current.LocalSettings;
                localSettings.Values.Remove("AuthToken");
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
            return !string.IsNullOrEmpty(token);
        }

        public async Task LogoutAsync()
        {
            await ClearAuthTokenAsync();
        }

        public async Task<UserDto?> GetCurrentUserAsync()
        {
            return await GetAsync<UserDto>("auth/me");
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
                // ========================================
                // Call Python Brain backend (LLM-First v2)
                // Production: Render
                // ========================================
                var pythonBackendUrl = "http://localhost:8000/api/agent/plan/v2";
                
                using var client = new HttpClient();
                client.Timeout = TimeSpan.FromSeconds(30);
                
                var requestBody = new { command = commandText };
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
                System.Diagnostics.Debug.WriteLine($"[COMMAND] Response: {responseJson}");
                
                // Parse and execute using SmartExecutor for reliable execution
                using var doc = JsonDocument.Parse(responseJson);
                var root = doc.RootElement;
                
                if (root.TryGetProperty("steps", out JsonElement stepsElement))
                {
                    // Use SmartExecutor for retry logic, timing, and VISION RECOVERY
                    var executor = new SmartExecutor();
                    executor.SetOriginalGoal(commandText);  // Pass original command for vision recovery
                    var result = await executor.ExecutePlanAsync(stepsElement);
                    
                    if (!result.Success)
                    {
                        System.Diagnostics.Debug.WriteLine($"[COMMAND] Plan execution failed: {result.Error}");
                    }
                    else
                    {
                        System.Diagnostics.Debug.WriteLine($"[COMMAND] Plan completed: {result.ActionResults.Count} actions in {result.TotalExecutionTimeMs}ms");
                    }
                }
                
                return responseJson;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[COMMAND] Error: {ex.Message}");
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
                if (string.IsNullOrEmpty(token)) return new List<SkillDto>();

                using var client = new HttpClient();
                client.DefaultRequestHeaders.Authorization = 
                    new AuthenticationHeaderValue("Bearer", token);

                var response = await client.GetAsync($"{MICROSERVICE_URL}/me/skills");
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    var skills = JsonSerializer.Deserialize<List<SkillDto>>(json, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                    return skills ?? new List<SkillDto>();
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[API] GetMySkills error: {ex.Message}");
            }
            return new List<SkillDto>();
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
    }

    public class AuthResponse
    {
        public string Token { get; set; } = string.Empty;
        public UserDto User { get; set; } = new UserDto();
    }

    public class UserDto
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Email { get; set; } = string.Empty;
    }

    // =====================================================
    // DTOs for Real Backend Data
    // =====================================================

    public class SkillDto
    {
        public string Id { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public string IntentSignature { get; set; } = string.Empty;
        public string? Description { get; set; }
        public float Confidence { get; set; }
        public int SuccessCount { get; set; }
        public string? LastUsedAt { get; set; }
        public string? CreatedAt { get; set; }
    }

    public class SessionDto
    {
        public string SessionId { get; set; } = string.Empty;
        public string Intent { get; set; } = string.Empty;
        public string StartedAt { get; set; } = string.Empty;
        public string? EndedAt { get; set; }
        public string Status { get; set; } = string.Empty;
        public float Confidence { get; set; }
        public int StepCount { get; set; }
    }

    public class MemoryDto
    {
        public List<string> FrequentSkills { get; set; } = new();
        public List<string> FailurePatterns { get; set; } = new();
        public List<string> SuccessPatterns { get; set; } = new();
        public string? UpdatedAt { get; set; }
    }

    public class DashboardStatsDto
    {
        public int TotalTasks { get; set; }
        public double SuccessRate { get; set; }
        public int AverageLatency { get; set; }
        public string Uptime { get; set; } = string.Empty;
        public int ActiveSkills { get; set; }
    }
}

