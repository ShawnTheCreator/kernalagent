using Google.Cloud.Firestore;

namespace KernalAgentBackend.Data
{
    [FirestoreData]
    public class User
    {
        [FirestoreProperty("email")]
        public string Email { get; set; }

        [FirestoreProperty("created_at")]
        public Timestamp CreatedAt { get; set; }

        [FirestoreProperty("neural_credits")]
        public int NeuralCredits { get; set; }

        [FirestoreProperty("settings")]
        public Dictionary<string, string> Settings { get; set; }
    }
}
