using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;

namespace Kernel_Agent
{
    // The class name MUST be SandboxPage to match the XAML
    public sealed partial class SandboxPage : Page
    {
        public SandboxPage()
        {
            InitializeComponent();
        }

        private void RunSandboxButton_Click(object sender, RoutedEventArgs e)
        {
            // Simulate running code: echo input to output
            SandboxOutput.Text = $"You entered: {SandboxInput.Text}";
        }

        private async void VoiceMicButton_Click(object sender, RoutedEventArgs e)
        {
            SandboxOutput.Text = "Listening...";
            string transcript = await RecognizeSpeechFromMicAsync();
            SandboxInput.Text = transcript;
            if (!string.IsNullOrWhiteSpace(transcript))
            {
                SandboxOutput.Text = "Thinking...";
                var response = await Services.ApiService.Instance.AskAgentAsync(transcript);
                SandboxOutput.Text = response ?? "No response from agent.";
            }
            else
            {
                SandboxOutput.Text = "No speech detected.";
            }
        }

        private async Task<string> RecognizeSpeechFromMicAsync()
        {
            // Uses NAudio to record and Google.Cloud.Speech.V1 to transcribe
            // This is a simplified version; for production, handle cleanup and errors robustly
            var speech = SpeechClient.Create();
            var config = new RecognitionConfig
            {
                Encoding = RecognitionConfig.Types.AudioEncoding.Linear16,
                SampleRateHertz = 16000,
                LanguageCode = "en-US"
            };
            using (var ms = new MemoryStream())
            using (var waveIn = new WaveInEvent())
            {
                waveIn.WaveFormat = new WaveFormat(16000, 1);
                waveIn.DataAvailable += (s, a) => ms.Write(a.Buffer, 0, a.BytesRecorded);
                waveIn.StartRecording();
                await Task.Delay(4000); // Record for 4 seconds (adjust as needed)
                waveIn.StopRecording();
                ms.Position = 0;
                var audio = RecognitionAudio.FromStream(ms);
                var response = speech.Recognize(config, audio);
                foreach (var result in response.Results)
                {
                    return result.Alternatives[0].Transcript;
                }
            }
            return string.Empty;
        }
    }
}