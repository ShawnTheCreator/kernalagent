using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Speech.Recognition;
using Kernel_Agent.Services;

namespace Kernel_Agent.Services
{
    public class VoiceToActionService
    {
        private readonly WindowsAutomation _automation = new WindowsAutomation();
        private readonly string _pythonBackendUrl = "http://localhost:8000/api/agent/plan"; // Change to your deployed Python backend if needed
        private readonly SpeechRecognitionEngine _recognizer;

        public VoiceToActionService()
        {
            _recognizer = new SpeechRecognitionEngine();
            _recognizer.SetInputToDefaultAudioDevice();
            _recognizer.LoadGrammar(new DictationGrammar());
            _recognizer.SpeechRecognized += Recognizer_SpeechRecognized;
        }

        public void StartListening()
        {
            _recognizer.RecognizeAsync(RecognizeMode.Multiple);
        }

        public void StopListening()
        {
            _recognizer.RecognizeAsyncStop();
        }

        private async void Recognizer_SpeechRecognized(object sender, SpeechRecognizedEventArgs e)
        {
            string recognizedText = e.Result.Text;
            var actionPlan = await GetActionPlanFromPython(recognizedText);
            if (actionPlan != null)
            {
                await ExecuteActionPlan(actionPlan);
            }
        }

        private async Task<JsonElement[]> GetActionPlanFromPython(string userCommand)
        {
            using var client = new HttpClient();
            var requestBody = new { command = userCommand };
            var content = new StringContent(JsonSerializer.Serialize(requestBody), Encoding.UTF8, "application/json");
            var response = await client.PostAsync(_pythonBackendUrl, content);
            if (!response.IsSuccessStatusCode) return null;
            var json = await response.Content.ReadAsStringAsync();
            using var doc = JsonDocument.Parse(json);
            return doc.RootElement.EnumerateArray().ToArray();
        }

        private async Task ExecuteActionPlan(JsonElement[] steps)
        {
            foreach (var step in steps)
            {
                string action = step.GetProperty("action").GetString();
                switch (action)
                {
                    case "open_app":
                        _automation.OpenApplication(step.GetProperty("target").GetString());
                        await Task.Delay(2000);
                        break;
                    case "navigate":
                        _automation.TypeIntoApp(step.GetProperty("url").GetString() + "\n");
                        await Task.Delay(1500);
                        break;
                    case "search":
                        _automation.TypeIntoApp(step.GetProperty("query").GetString() + "\n");
                        await Task.Delay(1500);
                        break;
                    case "click":
                        // Implement click logic as needed
                        break;
                    case "type_text":
                        _automation.TypeIntoApp(step.GetProperty("content").GetString());
                        break;
                }
            }
        }
    }
}
