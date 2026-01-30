using System;
using System.Diagnostics;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Windows.Storage;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Manages WebSocket connection to the Python brain for real-time communication.
    /// 
    /// Responsibilities:
    /// - Connect to /ws/stream and identify as C# executor
    /// - Listen for run_skill commands from frontend
    /// - Report executed actions back to frontend dashboards
    /// - Handle reconnection on disconnect
    /// </summary>
    public class BrainConnectionService
    {
        private static BrainConnectionService? _instance;
        private static readonly object _lock = new object();
        
        private ClientWebSocket? _webSocket;
        private CancellationTokenSource? _cts;
        private bool _isConnected = false;
        private readonly string _wsUrl;
        private readonly string _sessionId;
        
        public event Action<string, string>? OnSkillExecutionRequested;
        public event Action<bool>? OnConnectionStateChanged;
        public event Action<string>? OnAgentOutput;
        public event Action<string>? OnAgentPrompt;
        public event Action<string, string>? OnAuthSuccess;
        
        public static BrainConnectionService Instance
        {
            get
            {
                if (_instance == null)
                {
                    lock (_lock)
                    {
                        _instance ??= new BrainConnectionService();
                    }
                }
                return _instance;
            }
        }

        private static string FormatActionPlan(JsonElement root)
        {
            try
            {
                if (!root.TryGetProperty("payload", out var payload))
                    return "Action plan received";

                var original = payload.TryGetProperty("original_command", out var oc) ? oc.GetString() : null;
                var steps = payload.TryGetProperty("steps", out var st) && st.ValueKind == JsonValueKind.Array ? st.GetArrayLength() : 0;
                var reply = payload.TryGetProperty("brain_reply", out var br) ? br.GetString() : null;

                var line = $"[Automation] Plan ({steps} step{(steps == 1 ? "" : "s")}): {original}";
                if (!string.IsNullOrWhiteSpace(reply))
                    line += $" — {reply}";
                return line;
            }
            catch
            {
                return "[Automation] Plan received";
            }
        }
        
        private BrainConnectionService()
        {
            _sessionId = GetOrCreateSessionId();
            var baseUrl = Environment.GetEnvironmentVariable("BRAIN_WS_URL") ?? "ws://localhost:8000/ws/stream";
            _wsUrl = AppendQuery(baseUrl, $"client_type=csharp&session_id={Uri.EscapeDataString(_sessionId)}");
        }
        
        public bool IsConnected => _isConnected;

        public async Task<bool> SendIntentAsync(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return false;
            if (!_isConnected)
            {
                await ConnectAsync();
            }

            if (!_isConnected) return false;

            await SendMessageAsync(new
            {
                type = "intent_update",
                payload = text
            });

            return true;
        }
        
        /// <summary>
        /// Connect to the Python brain WebSocket.
        /// </summary>
        public async Task ConnectAsync()
        {
            if (_isConnected)
            {
                Debug.WriteLine("[BRAIN] Already connected");
                return;
            }
            
            try
            {
                _cts = new CancellationTokenSource();
                _webSocket = new ClientWebSocket();
                
                Debug.WriteLine($"[BRAIN] Connecting to {_wsUrl}...");
                await _webSocket.ConnectAsync(new Uri(_wsUrl), _cts.Token);
                _isConnected = true;
                Debug.WriteLine("[BRAIN] Connected to Python brain");
                
                // Identify as C# executor
                await SendMessageAsync(new
                {
                    type = "identify",
                    client_type = "csharp"
                });
                
                OnConnectionStateChanged?.Invoke(true);
                
                // Start listening for messages
                _ = Task.Run(ListenForMessagesAsync);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[BRAIN] Connection failed: {ex.Message}");
                _isConnected = false;
                OnConnectionStateChanged?.Invoke(false);
                
                // Schedule reconnect
                _ = Task.Run(async () =>
                {
                    await Task.Delay(5000);
                    await ConnectAsync();
                });
            }
        }
        
        /// <summary>
        /// Listen for incoming WebSocket messages.
        /// </summary>
        private async Task ListenForMessagesAsync()
        {
            var buffer = new byte[4096];
            
            try
            {
                while (_webSocket?.State == WebSocketState.Open && !_cts!.Token.IsCancellationRequested)
                {
                    var result = await _webSocket.ReceiveAsync(
                        new ArraySegment<byte>(buffer), 
                        _cts.Token
                    );
                    
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        Debug.WriteLine("[BRAIN] Server closed connection");
                        break;
                    }
                    
                    if (result.MessageType == WebSocketMessageType.Text)
                    {
                        var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                        await HandleMessageAsync(message);
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[BRAIN] Receive error: {ex.Message}");
            }
            finally
            {
                _isConnected = false;
                OnConnectionStateChanged?.Invoke(false);
                
                // Reconnect after disconnect
                Debug.WriteLine("[BRAIN] Scheduling reconnect in 5 seconds...");
                await Task.Delay(5000);
                await ConnectAsync();
            }
        }
        
        /// <summary>
        /// Handle incoming WebSocket message.
        /// </summary>
        private async Task HandleMessageAsync(string message)
        {
            try
            {
                var json = JsonDocument.Parse(message);
                var type = json.RootElement.GetProperty("type").GetString();
                
                Debug.WriteLine($"[BRAIN] Received: {type}");
                
                switch (type)
                {
                    case "auth_success":
                        if (json.RootElement.TryGetProperty("deviceId", out var devEl) &&
                            json.RootElement.TryGetProperty("token", out var tokenEl))
                        {
                            var deviceId = devEl.GetString() ?? string.Empty;
                            var token = tokenEl.GetString() ?? string.Empty;
                            if (!string.IsNullOrWhiteSpace(deviceId) && !string.IsNullOrWhiteSpace(token))
                            {
                                OnAuthSuccess?.Invoke(deviceId, token);
                            }
                        }
                        break;

                    case "run_skill":
                        var skillId = json.RootElement.GetProperty("skill_id").GetString();
                        var skillName = json.RootElement.TryGetProperty("skill_name", out var nameElem) 
                            ? nameElem.GetString() 
                            : skillId;
                        
                        Debug.WriteLine($"[BRAIN] Skill execution requested: {skillName}");
                        OnSkillExecutionRequested?.Invoke(skillId!, skillName!);
                        
                        // Execute the skill
                        await ExecuteSkillAsync(skillId!, skillName!);
                        break;

                    case "chat_response":
                        if (json.RootElement.TryGetProperty("payload", out var chatPayload) &&
                            chatPayload.TryGetProperty("message", out var msgElem))
                        {
                            OnAgentOutput?.Invoke(msgElem.GetString() ?? string.Empty);
                        }
                        break;

                    case "ask_question":
                        if (json.RootElement.TryGetProperty("payload", out var askPayload) &&
                            askPayload.TryGetProperty("question", out var qElem))
                        {
                            OnAgentPrompt?.Invoke(qElem.GetString() ?? string.Empty);
                        }
                        break;

                    case "action_plan":
                        OnAgentOutput?.Invoke(FormatActionPlan(json.RootElement));
                        break;
                        
                    case "action":
                        // Action plan from vision analysis - already handled by existing flow
                        break;
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[BRAIN] Message parsing error: {ex.Message}");
            }
        }
        
        /// <summary>
        /// Execute a skill by ID.
        /// </summary>
        private async Task ExecuteSkillAsync(string skillId, string skillName)
        {
            try
            {
                Debug.WriteLine($"[BRAIN] Executing skill: {skillName}");
                
                // Notify that we're starting
                await ReportActionAsync("skill_start", skillName, $"Starting skill: {skillName}");
                
                // Use SkillRecorder to play the skill
                var result = await SkillRecorder.Instance.PlaySkillAsync(skillName);
                
                if (result)
                {
                    Debug.WriteLine($"[BRAIN] Skill completed: {skillName}");
                    await ReportActionAsync("skill_complete", skillName, $"Skill completed successfully");
                }
                else
                {
                    Debug.WriteLine($"[BRAIN] Skill failed: {skillName}");
                    await ReportActionAsync("skill_failed", skillName, $"Skill execution failed");
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[BRAIN] Skill execution error: {ex.Message}");
                await ReportActionAsync("skill_error", skillName, ex.Message);
            }
        }
        
        /// <summary>
        /// Report an executed action to the Python brain for broadcasting to frontends.
        /// </summary>
        public async Task ReportActionAsync(string action, string target, string content = "")
        {
            if (!_isConnected) return;
            
            await SendMessageAsync(new
            {
                type = "action_executed",
                payload = new
                {
                    action = action,
                    target = target,
                    content = content,
                    timestamp = DateTime.UtcNow.ToString("o")
                }
            });
            
            Debug.WriteLine($"[BRAIN] Reported action: {action} -> {target}");
        }
        
        /// <summary>
        /// Send a message to the WebSocket server.
        /// </summary>
        private async Task SendMessageAsync(object message)
        {
            if (_webSocket?.State != WebSocketState.Open) return;
            
            try
            {
                var json = JsonSerializer.Serialize(message);
                var bytes = Encoding.UTF8.GetBytes(json);
                await _webSocket.SendAsync(
                    new ArraySegment<byte>(bytes),
                    WebSocketMessageType.Text,
                    true,
                    _cts!.Token
                );
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[BRAIN] Send error: {ex.Message}");
            }
        }

        private static string AppendQuery(string baseUrl, string query)
        {
            if (string.IsNullOrWhiteSpace(query)) return baseUrl;
            if (baseUrl.Contains("?"))
                return baseUrl + "&" + query;
            return baseUrl + "?" + query;
        }

        private static string GetOrCreateSessionId()
        {
            // Best-effort persistence; LocalSettings may throw depending on thread.
            try
            {
                var settings = ApplicationData.Current.LocalSettings;
                if (settings.Values.TryGetValue("BrainSessionId", out var existing) && existing is string s && !string.IsNullOrWhiteSpace(s))
                    return s;

                var created = Guid.NewGuid().ToString();
                settings.Values["BrainSessionId"] = created;
                return created;
            }
            catch
            {
                return Guid.NewGuid().ToString();
            }
        }
        
        /// <summary>
        /// Disconnect from the WebSocket server.
        /// </summary>
        public async Task DisconnectAsync()
        {
            _cts?.Cancel();
            
            if (_webSocket?.State == WebSocketState.Open)
            {
                try
                {
                    await _webSocket.CloseAsync(
                        WebSocketCloseStatus.NormalClosure,
                        "Client closing",
                        CancellationToken.None
                    );
                }
                catch { }
            }
            
            _isConnected = false;
            OnConnectionStateChanged?.Invoke(false);
            Debug.WriteLine("[BRAIN] Disconnected");
        }
    }
}
