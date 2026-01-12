using Google.Cloud.Firestore;
using System;
using System.Threading.Tasks;

namespace Kernel_Agent.Services
{
    public class FirestoreRealtimeListener
    {
        private FirestoreDb _firestoreDb;
        private ListenerRegistration _listenerRegistration;

        public FirestoreRealtimeListener(string projectId, string sessionId)
        {
            _firestoreDb = FirestoreDb.Create(projectId);
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
                    // Update your UI with the new monologue text
                    // Example: MainWindow.Instance.UpdateMonologueBox(monologue);
                }
            });
        }

        public void StopListening()
        {
            _listenerRegistration?.Stop();
        }
    }
}
