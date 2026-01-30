using System;
using System.IO;
using System.Threading.Tasks;
using NAudio.Wave;
using NAudio.Lame;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Handles audio playback using NAudio.
    /// Supports MP3 and WAV formats.
    /// </summary>
    public class AudioPlaybackService
    {
        private static AudioPlaybackService? _instance;
        private IWavePlayer? _wavePlayer;
        private WaveStream? _waveStream;
        private MemoryStream? _audioStream;
        private bool _isPlaying;

        public static AudioPlaybackService Instance
        {
            get
            {
                _instance ??= new AudioPlaybackService();
                return _instance;
            }
        }

        private AudioPlaybackService()
        {
            _isPlaying = false;
        }

        /// <summary>
        /// Play audio from byte array (MP3 or WAV).
        /// </summary>
        public async Task PlayAudioAsync(byte[] audioBytes)
        {
            if (audioBytes == null || audioBytes.Length == 0)
            {
                System.Diagnostics.Debug.WriteLine("[AUDIO] No audio data to play");
                return;
            }

            try
            {
                // Stop any currently playing audio
                StopAudio();

                // Create a memory stream from the byte array.
                // IMPORTANT: Keep this stream alive for the duration of playback.
                _audioStream = new MemoryStream(audioBytes);

                // Detect format and create appropriate wave stream
                _waveStream = CreateWaveStream(_audioStream);
                if (_waveStream == null)
                {
                    System.Diagnostics.Debug.WriteLine("[AUDIO] Could not create wave stream");
                    return;
                }

                // Initialize wave player
                _wavePlayer = new WaveOutEvent();
                _wavePlayer.Init(_waveStream);

                // Set up completion handler
                _wavePlayer.PlaybackStopped += OnPlaybackStopped;

                // Start playback
                _wavePlayer.Play();
                _isPlaying = true;

                System.Diagnostics.Debug.WriteLine($"[AUDIO] Playing {audioBytes.Length} bytes of audio");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUDIO] Playback error: {ex.Message}");
                Cleanup();
            }
        }

        /// <summary>
        /// Stop current audio playback.
        /// </summary>
        public void StopAudio()
        {
            if (_wavePlayer != null && _isPlaying)
            {
                _wavePlayer.Stop();
            }
            Cleanup();
        }

        /// <summary>
        /// Check if audio is currently playing.
        /// </summary>
        public bool IsPlaying => _isPlaying;

        private WaveStream? CreateWaveStream(Stream audioStream)
        {
            try
            {
                // Try to detect format by reading the first few bytes
                var buffer = new byte[12];
                var originalPosition = audioStream.Position;
                audioStream.Read(buffer, 0, 12);
                audioStream.Position = originalPosition;

                // Check for MP3 header (ID3 or MP3 sync)
                if (IsMp3Format(buffer))
                {
                    return new Mp3FileReader(audioStream);
                }

                // Check for WAV header
                if (IsWavFormat(buffer))
                {
                    return new WaveFileReader(audioStream);
                }

                // Default: try MP3 first, then WAV
                try
                {
                    audioStream.Position = originalPosition;
                    return new Mp3FileReader(audioStream);
                }
                catch
                {
                    try
                    {
                        audioStream.Position = originalPosition;
                        return new WaveFileReader(audioStream);
                    }
                    catch
                    {
                        return null;
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUDIO] Format detection error: {ex.Message}");
                return null;
            }
        }

        private static bool IsMp3Format(byte[] header)
        {
            // Check for ID3v2 tag
            if (header.Length >= 10 && 
                header[0] == 'I' && header[1] == 'D' && header[2] == '3')
            {
                return true;
            }

            // Check for MP3 sync word (11 consecutive set bits)
            if (header.Length >= 3 &&
                ((header[0] & 0xFF) == 0xFF) &&
                ((header[1] & 0xE0) == 0xE0))
            {
                return true;
            }

            return false;
        }

        private static bool IsWavFormat(byte[] header)
        {
            return header.Length >= 12 &&
                   header[0] == 'R' && header[1] == 'I' &&
                   header[2] == 'F' && header[3] == 'F' &&
                   header[8] == 'W' && header[9] == 'A' &&
                   header[10] == 'V' && header[11] == 'E';
        }

        private void OnPlaybackStopped(object? sender, StoppedEventArgs e)
        {
            _isPlaying = false;
            Cleanup();
        }

        private void Cleanup()
        {
            try
            {
                _wavePlayer?.Stop();
                _wavePlayer?.Dispose();
                _wavePlayer = null;

                _waveStream?.Dispose();
                _waveStream = null;

                _audioStream?.Dispose();
                _audioStream = null;

                _isPlaying = false;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUDIO] Cleanup error: {ex.Message}");
            }
        }
    }
}
