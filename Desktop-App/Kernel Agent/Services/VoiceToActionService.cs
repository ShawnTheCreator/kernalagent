using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Linq;
using System.Threading.Tasks;
using Kernel_Agent.Services;

namespace Kernel_Agent.Services
{
    public class VoiceToActionService
    {
        public VoiceToActionService()
        {
            System.Diagnostics.Debug.WriteLine("[VOICE] VoiceToActionService is disabled (migrated to WebSocket voice pipeline)");
        }

        public void StartListening()
        {
            // No-op: disabled to avoid microphone contention.
        }

        public void StopListening()
        {
            // No-op: disabled to avoid microphone contention.
        }
    }
}
