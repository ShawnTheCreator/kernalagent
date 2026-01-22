using System;
using System.Diagnostics;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

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
        
        public event Action<string, string>? OnSkillExecutionRequested;
        public event Action<bool>? OnConnectionStateChanged;
        
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
        
        private BrainConnectionService()
        {
            _wsUrl = Environment.GetEnvironmentVariable("BRAIN_WS_URL") ?? "ws://localhost:8000/ws/stream";
        }
        
        public bool IsConnected => _isConnected;
        
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
