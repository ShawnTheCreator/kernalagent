using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Test connection between C# Desktop Agent and Python Microservice.
    /// 
    /// Usage:
    ///     bool success = await AgentConnectionTest.TestConnectionAsync();
    /// </summary>
    public static class AgentConnectionTest
    {
        private static readonly string BASE_URL = "https://kernalagent.onrender.com";
        private static readonly string PLAN_ENDPOINT = "/api/agent/plan";

        /// <summary>
        /// Run full connection test. Check Debug Output for results.
        /// </summary>
        public static async Task<bool> TestConnectionAsync()
        {
            Console.WriteLine("========================================");
            Console.WriteLine("AGENT CONNECTION TEST");
            Console.WriteLine("========================================");

            try
            {
                using var client = new HttpClient
                {
                    BaseAddress = new Uri(BASE_URL),
                    Timeout = TimeSpan.FromSeconds(10)
                };

                // Test 1: Health check
                Console.WriteLine("\n[1] Testing health endpoint...");
                var healthResponse = await client.GetAsync("/health");
                if (!healthResponse.IsSuccessStatusCode)
                {
                    Console.WriteLine("    ✗ Health check failed!");
                    return false;
                }
                var healthJson = await healthResponse.Content.ReadAsStringAsync();
                Console.WriteLine($"    ✓ Health check passed: {healthJson}");

                // Test 2: Simple command
                Console.WriteLine("\n[2] Testing 'open notepad' command...");
                var result1 = await SendCommandAsync(client, "open notepad");
                if (result1 == null)
                {
                    Console.WriteLine("    ✗ Command failed!");
                    return false;
                }
                Console.WriteLine($"    ✓ Got {result1.Steps?.Length ?? 0} step(s)");

                // Test 3: Multi-step command
                Console.WriteLine("\n[3] Testing 'search for weather' command...");
                var result2 = await SendCommandAsync(client, "search for weather");
                if (result2 == null)
                {
                    Console.WriteLine("    ✗ Command failed!");
                    return false;
                }
                Console.WriteLine($"    ✓ Got {result2.Steps?.Length ?? 0} step(s)");

                Console.WriteLine("\n========================================");
                Console.WriteLine("✓ ALL TESTS PASSED - Connection is working!");
                Console.WriteLine("========================================");
                return true;
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine($"\n✗ CONNECTION ERROR: {ex.Message}");
                Console.WriteLine("\nIs the Python server running?");
                Console.WriteLine("Start it with:");
                Console.WriteLine("  cd kernalagent-contrib/Microservice");
                Console.WriteLine("  .\\venv\\Scripts\\activate");
                Console.WriteLine("  python standalone_agent_server.py");
                return false;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"\n✗ ERROR: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Send a command to the Python microservice.
        /// </summary>
        private static async Task<PlanResponse?> SendCommandAsync(HttpClient client, string command)
        {
            var requestBody = new { command };
            var json = JsonSerializer.Serialize(requestBody);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            var response = await client.PostAsync(PLAN_ENDPOINT, content);

            if (response.IsSuccessStatusCode)
            {
                var responseJson = await response.Content.ReadAsStringAsync();
                Console.WriteLine($"    Response: {responseJson}");

                return JsonSerializer.Deserialize<PlanResponse>(responseJson, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });
            }

            Console.WriteLine($"    HTTP Error: {response.StatusCode}");
            return null;
        }
    }

    /// <summary>
    /// Response from Python microservice.
    /// </summary>
    public class PlanResponse
    {
        public string SessionId { get; set; } = string.Empty;
        public ActionStep[]? Steps { get; set; }
        public string SchemaVersion { get; set; } = string.Empty;
    }

    /// <summary>
    /// Single action step from Python.
    /// </summary>
    public class ActionStep
    {
        public string Action { get; set; } = string.Empty;
        public string? Target { get; set; }
        public string? Url { get; set; }
        public string? Query { get; set; }
        public string? Content { get; set; }

        public override string ToString()
        {
            if (!string.IsNullOrEmpty(Target)) return $"{Action} -> {Target}";
            if (!string.IsNullOrEmpty(Content)) return $"{Action} -> \"{Content}\"";
            if (!string.IsNullOrEmpty(Url)) return $"{Action} -> {Url}";
            return Action;
        }
    }
}
