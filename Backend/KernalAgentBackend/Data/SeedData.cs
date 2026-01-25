using Google.Cloud.Firestore;

namespace KernalAgentBackend.Data
{
    public static class SeedData
    {
        public static async Task SeedUsers(FirestoreDb db)
        {
            var usersCollection = db.Collection("users");
            var snapshot = await usersCollection.Limit(1).GetSnapshotAsync();
            if (snapshot.Documents.Count > 0)
            {
                Console.WriteLine("Users collection already contains data. Skipping seed.");
                return;
            }

            var user = new User
            {
                Email = "testuser@example.com",
                CreatedAt = Timestamp.FromDateTime(DateTime.UtcNow),
                NeuralCredits = 500,
                Settings = new Dictionary<string, string>
                {
                    { "theme", "dark" }
                }
            };

            await usersCollection.Document("abc123xyz").SetAsync(user);
            Console.WriteLine("Seeded initial user data.");
        }
    }
}
