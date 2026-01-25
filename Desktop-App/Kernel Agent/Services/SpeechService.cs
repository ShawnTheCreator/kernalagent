using System;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using NAudio.Wave;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Service to handle voice recording and transcription via Python API.
    /// Uses NAudio for recording and Python speech_recognition for transcription.
    /// </summary>
    public class SpeechService : IDisposable
    {
        private readonly HttpClient _client;
        private WaveInEvent? _waveIn;
        private MemoryStream? _audioBuffer;
        private WaveFileWriter? _waveWriter;
        
        private bool _isRecording = false;
        private readonly string _transcribeUrl = "http://localhost:8000/api/speech/transcribe";
        
        public event Action<string>? OnTranscriptionReceived;
        public event Action<string>? OnError;
        public event Action<float>? OnAudioLevel;
        
        public SpeechService()
        {
            _client = new HttpClient
            {
                Timeout = TimeSpan.FromSeconds(30)
            };
        }
        
        /// <summary>
        /// Start recording audio from microphone.
        /// </summary>
        public void StartRecording()
        {
            if (_isRecording) return;
            
            try
            {
                // Create buffer for audio data
                _audioBuffer = new MemoryStream();
                
                // Configure wave format (16kHz, 16-bit, mono for speech recognition)
                var waveFormat = new WaveFormat(16000, 16, 1);
                
                // Create wave writer to buffer
                _waveWriter = new WaveFileWriter(_audioBuffer, waveFormat);
                
                // Create wave input from default microphone
                _waveIn = new WaveInEvent
                {
                    WaveFormat = waveFormat,
                    BufferMilliseconds = 100
                };
                
                _waveIn.DataAvailable += (s, e) =>
                {
                    // Write audio data to buffer
                    _waveWriter?.Write(e.Buffer, 0, e.BytesRecorded);
                    
                    // Calculate audio level for visual feedback
                    float maxLevel = 0;
                    for (int i = 0; i < e.BytesRecorded; i += 2)
                    {
                        short sample = (short)(e.Buffer[i] | (e.Buffer[i + 1] << 8));
                        float level = Math.Abs(sample / 32768f);
                        maxLevel = Math.Max(maxLevel, level);
                    }
                    OnAudioLevel?.Invoke(maxLevel);
                };
                
                _waveIn.RecordingStopped += (s, e) =>
                {
                    System.Diagnostics.Debug.WriteLine("[SPEECH] Recording stopped");
                };
                
                _waveIn.StartRecording();
                _isRecording = true;
                
                System.Diagnostics.Debug.WriteLine("[SPEECH] Recording started (16kHz, mono)");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SPEECH] Error starting recording: {ex.Message}");
                OnError?.Invoke($"Recording error: {ex.Message}");
            }
        }
        
        /// <summary>
        /// Stop recording and send audio to Python for transcription.
        /// </summary>
        public async Task<string?> StopAndTranscribeAsync()
        {
            if (!_isRecording) return null;
            
            try
            {
                _isRecording = false;
                
                // Stop recording
                _waveIn?.StopRecording();
                _waveIn?.Dispose();
                _waveIn = null;
                
                // IMPORTANT: Get the audio bytes BEFORE disposing WaveFileWriter
                // because WaveFileWriter.Dispose() also closes the underlying MemoryStream
                _waveWriter?.Flush();
                
                if (_audioBuffer == null || _audioBuffer.Length < 1000)
                {
                    System.Diagnostics.Debug.WriteLine("[SPEECH] Audio too short, skipping transcription");
                    _waveWriter?.Dispose();
                    _waveWriter = null;
                    _audioBuffer?.Dispose();
                    _audioBuffer = null;
                    return null;
                }
                
                // Get WAV bytes BEFORE disposing writer (which closes the stream)
                byte[] audioBytes = _audioBuffer.ToArray();
                
                // Now safe to dispose
                _waveWriter?.Dispose();
                _waveWriter = null;
                _audioBuffer?.Dispose();
                _audioBuffer = null;
                
                System.Diagnostics.Debug.WriteLine($"[SPEECH] Sending {audioBytes.Length} bytes to Python");
                
                // Send to Python API
                string base64Audio = Convert.ToBase64String(audioBytes);
                var requestBody = new
                {
                    audio_base64 = base64Audio,
                    format = "wav"
                };
                
                var json = JsonSerializer.Serialize(requestBody);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                
                var response = await _client.PostAsync(_transcribeUrl, content);
                var responseText = await response.Content.ReadAsStringAsync();
                
                System.Diagnostics.Debug.WriteLine($"[SPEECH] Python response: {responseText}");
                
                if (response.IsSuccessStatusCode)
                {
                    var result = JsonSerializer.Deserialize<TranscribeResult>(responseText);
                    if (!string.IsNullOrEmpty(result?.text))
                    {
                        System.Diagnostics.Debug.WriteLine($"[SPEECH] Transcription: '{result.text}'");
                        OnTranscriptionReceived?.Invoke(result.text);
                        return result.text;
                    }
                }
                
                return null;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[SPEECH] Transcription error: {ex.Message}");
                OnError?.Invoke($"Transcription error: {ex.Message}");
                return null;
            }
        }
        
        /// <summary>
        /// Stop recording without transcribing.
        /// </summary>
        public void CancelRecording()
        {
            _isRecording = false;
            _waveIn?.StopRecording();
            _waveIn?.Dispose();
            _waveIn = null;
            _waveWriter?.Dispose();
            _waveWriter = null;
            _audioBuffer?.Dispose();
            _audioBuffer = null;
        }
        
        public bool IsRecording => _isRecording;
        
        public void Dispose()
        {
            CancelRecording();
            _client.Dispose();
        }
        
        private class TranscribeResult
        {
            public string? text { get; set; }
            public float confidence { get; set; }
            public string? source { get; set; }
            public string? error { get; set; }
        }
    }
}
