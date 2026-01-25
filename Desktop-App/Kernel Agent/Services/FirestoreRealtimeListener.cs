using Google.Cloud.Firestore;
using System;
using System.Threading.Tasks;

namespace Kernel_Agent.Services
{
    public class FirestoreRealtimeListener
    {
        private FirestoreDb _firestoreDb;
        private FirestoreChangeListener? _listenerRegistration;

        private Action<string> _onUpdate;

        public FirestoreRealtimeListener(string projectId, string sessionId, Action<string> onUpdate)
        {
            _firestoreDb = FirestoreDb.Create(projectId);
            _onUpdate = onUpdate;
            ListenToAgentSession(sessionId);
        }

        public void ListenToAgentSession(string sessionId)
        {
            var docRef = _firestoreDb.Collection("agent_sessions").Document(sessionId);
            _listenerRegistration = docRef.Listen(snapshot =>
            {
                if (snapshot.Exists)
                {
                    var data = snapshot.ToDictionary();
                    var monologue = data.ContainsKey("monologue") ? data["monologue"]?.ToString() : string.Empty;
                    _onUpdate?.Invoke(monologue ?? "");
                }
            });

        }

        public void StopListening()
        {
            _listenerRegistration = null;
        }
    }
}
