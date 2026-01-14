using System;
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
        
        private static readonly string BASE_URL = "https://kernal-agent-brain.onrender.com/"; // Python microservice - Not used directly anymore?
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

        private async Task SetAuthTokenAsync(string token)
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
                var url = $"auth/poll?deviceId={deviceId}";
                System.Diagnostics.Debug.WriteLine($"[API] Polling: {API_BASE_URL}{url}");
                
                var response = await _httpClient!.GetAsync(url);
                
                System.Diagnostics.Debug.WriteLine($"[API] Poll response status: {response.StatusCode}");
                
                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[API] Poll response body: {responseJson}");
                    
                    var authResponse = JsonSerializer.Deserialize<AuthResponse>(responseJson, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });

                    if (authResponse != null && !string.IsNullOrEmpty(authResponse.Token))
                    {
                        System.Diagnostics.Debug.WriteLine("[API] Token received! Saving...");
                        await SetAuthTokenAsync(authResponse.Token);
                        return true;
                    }
                    else
                    {
                        System.Diagnostics.Debug.WriteLine("[API] Response OK but no token in body");
                    }
                }
                else if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
                {
                    // 404 with "Login pending" is expected - not an error
                    var responseBody = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[API] Login pending (404): {responseBody}");
                    return false; // Keep polling
                }
                else
                {
                    var errorBody = await response.Content.ReadAsStringAsync();
                    System.Diagnostics.Debug.WriteLine($"[API] Poll failed with status {response.StatusCode}: {errorBody}");
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
                // FIXED: Call Python Brain backend directly
                // ========================================
                var pythonBackendUrl = "https://kernalagent.onrender.com/api/agent/plan";
                
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
                
                // Parse and execute the action steps
                using var doc = JsonDocument.Parse(responseJson);
                var root = doc.RootElement;
                
                if (root.TryGetProperty("steps", out JsonElement stepsElement))
                {
                    var automation = new WindowsAutomation();
                    
                    foreach (var step in stepsElement.EnumerateArray())
                    {
                        if (step.TryGetProperty("action", out JsonElement actionElement))
                        {
                            string action = actionElement.GetString() ?? "";
                            System.Diagnostics.Debug.WriteLine($"[COMMAND] Executing: {action}");
                            
                            switch (action)
                            {
                                case "open_app":
                                    if (step.TryGetProperty("target", out JsonElement targetEl))
                                    {
                                        string target = targetEl.GetString() ?? "";
                                        automation.OpenApplication(target);
                                        await Task.Delay(2000);
                                    }
                                    break;
                                    
                                case "type_text":
                                    if (step.TryGetProperty("content", out JsonElement contentEl))
                                    {
                                        string text = contentEl.GetString() ?? "";
                                        automation.TypeIntoApp(text);
                                    }
                                    break;
                                    
                                case "navigate":
                                    if (step.TryGetProperty("url", out JsonElement urlEl))
                                    {
                                        string url = urlEl.GetString() ?? "";
                                        automation.TypeIntoApp(url + "\n");
                                        await Task.Delay(1500);
                                    }
                                    break;
                            }
                        }
                    }
                }
                
                return responseJson;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[COMMAND] Error: {ex.Message}");
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
        public string Name { get; set; } = string.Empty;
        public string Email { get; set; } = string.Empty;
    }
}

