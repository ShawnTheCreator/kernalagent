using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;

namespace KernalAgentBackend.Services;

public class DeviceAuthWebSocketManager
{
    private readonly ConcurrentDictionary<string, ConcurrentDictionary<Guid, WebSocket>> _socketsByDeviceId = new();

    public Guid Register(string deviceId, WebSocket socket)
    {
        var connectionId = Guid.NewGuid();
        var deviceSockets = _socketsByDeviceId.GetOrAdd(deviceId, _ => new ConcurrentDictionary<Guid, WebSocket>());
        deviceSockets[connectionId] = socket;
        return connectionId;
    }

    public void Unregister(string deviceId, Guid connectionId)
    {
        if (_socketsByDeviceId.TryGetValue(deviceId, out var deviceSockets))
        {
            deviceSockets.TryRemove(connectionId, out _);
            if (deviceSockets.IsEmpty)
            {
                _socketsByDeviceId.TryRemove(deviceId, out _);
            }
        }
    }

    public async Task<int> SendAuthSuccessAsync(string deviceId, string token, CancellationToken cancellationToken = default)
    {
        if (!_socketsByDeviceId.TryGetValue(deviceId, out var deviceSockets) || deviceSockets.IsEmpty)
        {
            return 0;
        }

        var payload = JsonSerializer.Serialize(new
        {
            type = "auth_success",
            deviceId,
            token
        });

        var bytes = Encoding.UTF8.GetBytes(payload);
        var segment = new ArraySegment<byte>(bytes);

        var sent = 0;
        foreach (var kvp in deviceSockets)
        {
            var socket = kvp.Value;
            if (socket.State != WebSocketState.Open)
            {
                continue;
            }

            try
            {
                await socket.SendAsync(segment, WebSocketMessageType.Text, endOfMessage: true, cancellationToken);
                sent++;
            }
            catch
            {
                // Ignore; the receiver loop will clean up.
            }
        }

        return sent;
    }
}
