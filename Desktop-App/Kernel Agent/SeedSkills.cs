using System;
using System.IO;
using System.Threading.Tasks;
using Google.Apis.Auth.OAuth2;
using Google.Cloud.Firestore;
using FirebaseAdmin;
using dotenv.net;
using System.Collections.Generic;

namespace Kernel_Agent
{
    class SeedSkills
    {
        static async Task Main(string[] args)
        {
            // Load environment variables from .env file
            DotEnv.Load();

            // Build credential JSON from environment variables
            var credDict = new Dictionary<string, string>
            {
                {"type", Environment.GetEnvironmentVariable("FIREBASE_TYPE") ?? ""},
                {"project_id", Environment.GetEnvironmentVariable("FIREBASE_PROJECT_ID") ?? ""},
                {"private_key_id", Environment.GetEnvironmentVariable("FIREBASE_PRIVATE_KEY_ID") ?? ""},
                {"private_key", Environment.GetEnvironmentVariable("FIREBASE_PRIVATE_KEY")?.Replace("\\n", "\n") ?? ""},
                {"client_email", Environment.GetEnvironmentVariable("FIREBASE_CLIENT_EMAIL") ?? ""},
                {"client_id", Environment.GetEnvironmentVariable("FIREBASE_CLIENT_ID") ?? ""},
                {"auth_uri", Environment.GetEnvironmentVariable("FIREBASE_AUTH_URI") ?? ""},
                {"token_uri", Environment.GetEnvironmentVariable("FIREBASE_TOKEN_URI") ?? ""},
                {"auth_provider_x509_cert_url", Environment.GetEnvironmentVariable("FIREBASE_AUTH_PROVIDER_X509_CERT_URL") ?? ""},
                {"client_x509_cert_url", Environment.GetEnvironmentVariable("FIREBASE_CLIENT_X509_CERT_URL") ?? ""},
                {"universe_domain", Environment.GetEnvironmentVariable("FIREBASE_UNIVERSE_DOMAIN") ?? ""}
            };
            var credJson = System.Text.Json.JsonSerializer.Serialize(credDict);
            var credPath = Path.GetTempFileName();
            File.WriteAllText(credPath, credJson);

            FirebaseApp.Create(new AppOptions()
            {
                Credential = GoogleCredential.FromFile(credPath),
            });

            FirestoreDb db = FirestoreDb.Create(credDict["project_id"]);

            DocumentReference docRef = db.Collection("skills").Document("sample-skill");
            var skill = new
            {
                id = "sample-skill",
                name = "Open Word and Type",
                intent_signature = "open word and type",
                steps = new object[]
                {
                    new { action = "open_app", app = "Word" },
                    new { action = "type_text", text = "Hello, world!" }
                },
                created_at = DateTime.UtcNow,
                last_used_at = (DateTime?)null,
                success_count = 0
            };
            await docRef.SetAsync(skill);
            Console.WriteLine("Skill seeded.");
        }
    }
}
