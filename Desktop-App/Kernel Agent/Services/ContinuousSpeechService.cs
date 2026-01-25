using System;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Voice recognition states matching Python backend.
    /// </summary>
    public enum VoiceState
    {
        Idle,
        Listening,
        Processing,
        Stopped,
        Disconnected
    }

    /// <summary>
    /// Continuous voice recognition service using WebSocket streaming.
    /// 
    /// Features:
    /// - Real-time transcription as you speak
    /// - Wake word detection ("hey kernel")
    /// - Stop word detection ("stop bud")
    /// - Automatic silence-based command submission
    /// </summary>
    public class ContinuousSpeechService : IDisposable
    {
        private ClientWebSocket? _webSocket;
        private CancellationTokenSource? _cancellationTokenSource;
        private Task? _receiveTask;
        
        private readonly string _wsUrl = "ws://localhost:8000/ws/voice";
        
        public VoiceState State { get; private set; } = VoiceState.Disconnected;
        
        // Events
        public event Action<string, bool>? OnTranscription;  // text, isFinal
        public event Action<string>? OnCommand;              // final command to execute
        public event Action? OnWakeWord;
        public event Action? OnStopWord;
        public event Action<VoiceState>? OnStateChanged;
        public event Action<string>? OnError;
        public event Action? OnConnected;
        public event Action? OnDisconnected;
        
        /// <summary>
        /// Connect to the voice WebSocket server.
        /// </summary>
        public async Task<bool> ConnectAsync()
        {
            if (_webSocket?.State == WebSocketState.Open)
            {
                System.Diagnostics.Debug.WriteLine("[VOICE-WS] Already connected");
                return true;
            }
            
            try
            {
                _webSocket = new ClientWebSocket();
                _cancellationTokenSource = new CancellationTokenSource();
                
                System.Diagnostics.Debug.WriteLine($"[VOICE-WS] Connecting to {_wsUrl}...");
                await _webSocket.ConnectAsync(new Uri(_wsUrl), _cancellationTokenSource.Token);
                
                System.Diagnostics.Debug.WriteLine("[VOICE-WS] ✓ Connected!");
                SetState(VoiceState.Idle);
                OnConnected?.Invoke();
                
                // Start receiving messages
                _receiveTask = ReceiveMessagesAsync(_cancellationTokenSource.Token);
                
                return true;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE-WS] Connection failed: {ex.Message}");
                OnError?.Invoke($"Connection failed: {ex.Message}");
                SetState(VoiceState.Disconnected);
                return false;
            }
        }
        
        /// <summary>
        /// Disconnect from the voice WebSocket server.
        /// </summary>
        public async Task DisconnectAsync()
        {
            try
            {
                _cancellationTokenSource?.Cancel();
                
                if (_webSocket?.State == WebSocketState.Open)
                {
                    await _webSocket.CloseAsync(
                        WebSocketCloseStatus.NormalClosure, 
                        "Closing", 
                        CancellationToken.None
                    );
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE-WS] Disconnect error: {ex.Message}");
            }
            finally
            {
                _webSocket?.Dispose();
                _webSocket = null;
                SetState(VoiceState.Disconnected);
                OnDisconnected?.Invoke();
            }
        }
        
        /// <summary>
        /// Start continuous voice listening.
        /// </summary>
        public async Task StartListeningAsync(bool alwaysListening = true, float silenceTimeout = 1.5f)
        {
            if (_webSocket?.State != WebSocketState.Open)
            {
                var connected = await ConnectAsync();
                if (!connected) return;
            }
            
            var message = new
            {
                type = "start",
                config = new
                {
                    always_listening = alwaysListening,
                    silence_timeout = silenceTimeout
                }
            };
            
            await SendMessageAsync(message);
            System.Diagnostics.Debug.WriteLine("[VOICE-WS] Start listening command sent");
        }
        
        /// <summary>
        /// Stop continuous voice listening.
        /// </summary>
        public async Task StopListeningAsync()
        {
            if (_webSocket?.State != WebSocketState.Open) return;
            
            await SendMessageAsync(new { type = "stop" });
            System.Diagnostics.Debug.WriteLine("[VOICE-WS] Stop listening command sent");
        }
        
        /// <summary>
        /// Get current voice recognition status.
        /// </summary>
        public async Task GetStatusAsync()
        {
            if (_webSocket?.State != WebSocketState.Open) return;
            
            await SendMessageAsync(new { type = "status" });
        }
        
        private async Task SendMessageAsync(object message)
        {
            if (_webSocket?.State != WebSocketState.Open) return;
            
            var json = JsonSerializer.Serialize(message);
            var bytes = Encoding.UTF8.GetBytes(json);
            
            await _webSocket.SendAsync(
                new ArraySegment<byte>(bytes),
                WebSocketMessageType.Text,
                true,
                _cancellationTokenSource?.Token ?? CancellationToken.None
            );
        }
        
        private async Task ReceiveMessagesAsync(CancellationToken cancellationToken)
        {
            var buffer = new byte[4096];
            var messageBuilder = new StringBuilder();
            
            try
            {
                while (!cancellationToken.IsCancellationRequested && 
                       _webSocket?.State == WebSocketState.Open)
                {
                    var result = await _webSocket.ReceiveAsync(
                        new ArraySegment<byte>(buffer),
                        cancellationToken
                    );
                    
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        System.Diagnostics.Debug.WriteLine("[VOICE-WS] Server closed connection");
                        break;
                    }
                    
                    messageBuilder.Append(Encoding.UTF8.GetString(buffer, 0, result.Count));
                    
                    if (result.EndOfMessage)
                    {
                        var message = messageBuilder.ToString();
                        messageBuilder.Clear();
                        
                        ProcessMessage(message);
                    }
                }
            }
            catch (OperationCanceledException)
            {
                // Expected when cancelling
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE-WS] Receive error: {ex.Message}");
                OnError?.Invoke($"WebSocket error: {ex.Message}");
            }
            finally
            {
                SetState(VoiceState.Disconnected);
                OnDisconnected?.Invoke();
            }
        }
        
        private void ProcessMessage(string json)
        {
            try
            {
                using var doc = JsonDocument.Parse(json);
                var root = doc.RootElement;
                var msgType = root.GetProperty("type").GetString();
                
                System.Diagnostics.Debug.WriteLine($"[VOICE-WS] Received: {msgType}");
                
                switch (msgType)
                {
                    case "connected":
                        System.Diagnostics.Debug.WriteLine("[VOICE-WS] Server confirmed connection");
                        break;
                    
                    case "started":
                        var success = root.GetProperty("success").GetBoolean();
                        if (success)
                        {
                            SetState(VoiceState.Listening);
                        }
                        break;
                    
                    case "stopped":
                        SetState(VoiceState.Stopped);
                        break;
                    
                    case "transcription":
                        var text = root.GetProperty("text").GetString() ?? "";
                        var isFinal = root.GetProperty("is_final").GetBoolean();
                        System.Diagnostics.Debug.WriteLine($"[VOICE-WS] Transcription: '{text}' (final={isFinal})");
                        OnTranscription?.Invoke(text, isFinal);
                        break;
                    
                    case "command":
                        var command = root.GetProperty("text").GetString() ?? "";
                        System.Diagnostics.Debug.WriteLine($"[VOICE-WS] Command: '{command}'");
                        OnCommand?.Invoke(command);
                        break;
                    
                    case "wake_word":
                        System.Diagnostics.Debug.WriteLine("[VOICE-WS] Wake word detected!");
                        OnWakeWord?.Invoke();
                        break;
                    
                    case "stop_word":
                        System.Diagnostics.Debug.WriteLine("[VOICE-WS] Stop word detected!");
                        OnStopWord?.Invoke();
                        break;
                    
                    case "state":
                        var stateStr = root.GetProperty("state").GetString();
                        if (Enum.TryParse<VoiceState>(stateStr, true, out var newState))
                        {
                            SetState(newState);
                        }
                        break;
                    
                    case "error":
                        var error = root.GetProperty("error").GetString();
                        System.Diagnostics.Debug.WriteLine($"[VOICE-WS] Error: {error}");
                        OnError?.Invoke(error ?? "Unknown error");
                        break;
                    
                    case "pong":
                        // Keep-alive response
                        break;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE-WS] Parse error: {ex.Message}");
            }
        }
        
        private void SetState(VoiceState newState)
        {
            if (State != newState)
            {
                System.Diagnostics.Debug.WriteLine($"[VOICE-WS] State: {State} → {newState}");
                State = newState;
                OnStateChanged?.Invoke(newState);
            }
        }
        
        public void Dispose()
        {
            _cancellationTokenSource?.Cancel();
            _webSocket?.Dispose();
        }
    }
}
