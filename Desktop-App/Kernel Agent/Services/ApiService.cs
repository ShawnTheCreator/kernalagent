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
                // Call Python Brain backend (LLM-First v2)
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
                                // ===== APP CONTROL =====
                                case "open_app":
                                    if (step.TryGetProperty("target", out JsonElement targetEl))
                                    {
                                        automation.OpenApplication(targetEl.GetString() ?? "");
                                        await Task.Delay(2000);
                                    }
                                    break;
                                    
                                case "close_app":
                                    if (step.TryGetProperty("target", out JsonElement closeTargetEl))
                                    {
                                        automation.CloseApplication(closeTargetEl.GetString() ?? "");
                                    }
                                    break;
                                    
                                // ===== TEXT INPUT =====
                                case "type_text":
                                    if (step.TryGetProperty("content", out JsonElement contentEl))
                                    {
                                        automation.TypeIntoApp(contentEl.GetString() ?? "");
                                    }
                                    break;
                                    
                                case "navigate":
                                    if (step.TryGetProperty("url", out JsonElement urlEl))
                                    {
                                        automation.TypeIntoApp((urlEl.GetString() ?? "") + "\n");
                                        await Task.Delay(1500);
                                    }
                                    break;
                                    
                                // ===== VOLUME CONTROL =====
                                case "volume_up":
                                    int upAmount = 5;
                                    if (step.TryGetProperty("amount", out JsonElement upAmountEl))
                                        upAmount = upAmountEl.GetInt32() / 2; // Divide by 2 since each press is ~2%
                                    automation.VolumeUp(upAmount);
                                    break;
                                    
                                case "volume_down":
                                    int downAmount = 5;
                                    if (step.TryGetProperty("amount", out JsonElement downAmountEl))
                                        downAmount = downAmountEl.GetInt32() / 2;
                                    automation.VolumeDown(downAmount);
                                    break;
                                    
                                case "volume_mute":
                                    automation.VolumeMute();
                                    break;
                                    
                                case "volume_set":
                                    // For max volume, press up 50 times
                                    if (step.TryGetProperty("amount", out JsonElement setAmountEl) && setAmountEl.GetInt32() == 100)
                                        automation.VolumeUp(50);
                                    break;
                                    
                                // ===== WINDOW MANAGEMENT =====
                                case "minimize_window":
                                    automation.MinimizeWindow();
                                    break;
                                    
                                case "maximize_window":
                                    automation.MaximizeWindow();
                                    break;
                                    
                                case "restore_window":
                                    automation.RestoreWindow();
                                    break;
                                    
                                // ===== SYSTEM COMMANDS =====
                                case "lock_screen":
                                    automation.LockScreen();
                                    break;
                                    
                                case "sleep":
                                    automation.Sleep();
                                    break;
                                    
                                case "shutdown":
                                    automation.Shutdown();
                                    break;
                                    
                                case "restart":
                                    automation.Restart();
                                    break;
                                    
                                // ===== SCREENSHOT =====
                                case "screenshot":
                                    automation.TakeScreenshot();
                                    break;
                                
                                // ===== BRIGHTNESS =====
                                case "brightness_up":
                                    int brUpAmt = 10;
                                    if (step.TryGetProperty("amount", out JsonElement brUpEl))
                                        brUpAmt = brUpEl.GetInt32();
                                    automation.BrightnessUp(brUpAmt);
                                    break;
                                    
                                case "brightness_down":
                                    int brDownAmt = 10;
                                    if (step.TryGetProperty("amount", out JsonElement brDownEl))
                                        brDownAmt = brDownEl.GetInt32();
                                    automation.BrightnessDown(brDownAmt);
                                    break;
                                    
                                default:
                                    System.Diagnostics.Debug.WriteLine($"[COMMAND] Unknown action: {action}");
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
                return null;
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

