using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;
using System.IO;
using System.Linq;

namespace Kernel_Agent.Services
{
    public class ExecutionTrace
    {
        public string Id { get; set; } = Guid.NewGuid().ToString();
        public DateTime Timestamp { get; set; } = DateTime.UtcNow;
        public string Command { get; set; } = string.Empty;
        public string Interpretation { get; set; } = string.Empty;
        public string Plan { get; set; } = string.Empty;
        public List<ExecutionStep> Steps { get; set; } = new();
        public bool Success { get; set; }
        public string? Error { get; set; }
        public double? Confidence { get; set; }
        public long DurationMs { get; set; }
        public string Intent { get; set; } = string.Empty;
        public List<string> Entities { get; set; } = new();
        public List<string> Capabilities { get; set; } = new();
    }

    public class ExecutionStep
    {
        public string Action { get; set; } = string.Empty;
        public Dictionary<string, object> Parameters { get; set; } = new();
        public bool Success { get; set; }
        public string? Error { get; set; }
        public long DurationMs { get; set; }
    }

    public class CapabilityPattern
    {
        public string Id { get; set; } = Guid.NewGuid().ToString();
        public string Intent { get; set; } = string.Empty;
        public List<string> EntityTypes { get; set; } = new();
        public List<string> RequiredCapabilities { get; set; } = new();
        public List<string> TypicalActions { get; set; } = new();
        public double SuccessRate { get; set; }
        public int UsageCount { get; set; }
        public DateTime LastUsed { get; set; }
        public List<ExecutionTrace> Examples { get; set; } = new(3); // Keep only 3 examples
    }

    public class SafeMemoryLogger
    {
        private readonly string _logDirectory;
        private readonly string _tracesFile;
        private readonly string _patternsFile;
        private readonly object _lock = new();
        private List<ExecutionTrace> _traces = new();
        private List<CapabilityPattern> _patterns = new();

        public SafeMemoryLogger(string logDirectory = "logs")
        {
            _logDirectory = logDirectory;
            Directory.CreateDirectory(_logDirectory);
            _tracesFile = Path.Combine(_logDirectory, "execution_traces.jsonl");
            _patternsFile = Path.Combine(_logDirectory, "capability_patterns.json");
            
            LoadData();
        }

        private void LoadData()
        {
            lock (_lock)
            {
                // Load traces
                if (File.Exists(_tracesFile))
                {
                    try
                    {
                        var lines = File.ReadAllLines(_tracesFile);
                        _traces = lines
                            .Where(line => !string.IsNullOrWhiteSpace(line))
                            .Select(line => JsonSerializer.Deserialize<ExecutionTrace>(line))
                            .Where(trace => trace != null)
                            .ToList()!;
                    }
                    catch (Exception ex)
                    {
                        System.Diagnostics.Debug.WriteLine($"Failed to load traces: {ex.Message}");
                    }
                }

                // Load patterns
                if (File.Exists(_patternsFile))
                {
                    try
                    {
                        var json = File.ReadAllText(_patternsFile);
                        _patterns = JsonSerializer.Deserialize<List<CapabilityPattern>>(json) ?? new();
                    }
                    catch (Exception ex)
                    {
                        System.Diagnostics.Debug.WriteLine($"Failed to load patterns: {ex.Message}");
                    }
                }
            }
        }

        public async Task LogExecutionAsync(ExecutionTrace trace)
        {
            lock (_lock)
            {
                _traces.Add(trace);
                
                // Keep only last 1000 traces in memory
                if (_traces.Count > 1000)
                {
                    _traces = _traces.Skip(_traces.Count - 1000).ToList();
                }

                // Append to file (JSONL format for streaming)
                var line = JsonSerializer.Serialize(trace);
                File.AppendAllText(_tracesFile, line + Environment.NewLine);
            }

            // Update patterns asynchronously
            await UpdateCapabilityPatternsAsync(trace);
        }

        private async Task UpdateCapabilityPatternsAsync(ExecutionTrace trace)
        {
            await Task.Run(() =>
            {
                lock (_lock)
                {
                    // Find existing pattern or create new
                    var pattern = _patterns.FirstOrDefault(p => 
                        p.Intent.Equals(trace.Intent, StringComparison.OrdinalIgnoreCase) &&
                        p.EntityTypes.SequenceEqual(trace.Entities.OrderBy(e => e)));

                    if (pattern == null)
                    {
                        pattern = new CapabilityPattern
                        {
                            Intent = trace.Intent,
                            EntityTypes = new(trace.Entities),
                            RequiredCapabilities = new(trace.Capabilities),
                            TypicalActions = trace.Steps
                                .Where(s => s.Success)
                                .Select(s => s.Action)
                                .Distinct()
                                .ToList()
                        };
                        _patterns.Add(pattern);
                    }

                    // Update pattern statistics
                    pattern.UsageCount++;
                    pattern.LastUsed = DateTime.UtcNow;
                    
                    if (trace.Success)
                    {
                        pattern.SuccessRate = (pattern.SuccessRate * (pattern.UsageCount - 1) + 1.0) / pattern.UsageCount;
                    }
                    else
                    {
                        pattern.SuccessRate = (pattern.SuccessRate * (pattern.UsageCount - 1)) / pattern.UsageCount;
                    }

                    // Update examples (keep only successful ones)
                    if (trace.Success)
                    {
                        pattern.Examples.Add(trace);
                        if (pattern.Examples.Count > 3)
                        {
                            pattern.Examples.RemoveAt(0);
                        }
                    }

                    // Save patterns
                    var json = JsonSerializer.Serialize(_patterns, new JsonSerializerOptions { WriteIndented = true });
                    File.WriteAllText(_patternsFile, json);
                }
            });
        }

        public List<CapabilityPattern> GetRelevantPatterns(string intent, List<string> entities)
        {
            lock (_lock)
            {
                return _patterns
                    .Where(p => p.Intent.Equals(intent, StringComparison.OrdinalIgnoreCase))
                    .Where(p => p.SuccessRate >= 0.7) // Only return successful patterns
                    .Where(p => p.UsageCount >= 2) // Only well-established patterns
                    .OrderByDescending(p => p.SuccessRate)
                    .ThenByDescending(p => p.LastUsed)
                    .Take(5) // Limit to top 5
                    .ToList();
            }
        }

        public Dictionary<string, object> GetCapabilityStats()
        {
            lock (_lock)
            {
                var recentTraces = _traces
                    .Where(t => t.Timestamp > DateTime.UtcNow.AddDays(-7))
                    .ToList();

                return new Dictionary<string, object>
                {
                    ["total_traces"] = _traces.Count,
                    ["recent_traces_7days"] = recentTraces.Count,
                    ["success_rate_7days"] = recentTraces.Count > 0 
                        ? (double)recentTraces.Count(t => t.Success) / recentTraces.Count 
                        : 0.0,
                    ["unique_patterns"] = _patterns.Count,
                    ["high_confidence_patterns"] = _patterns.Count(p => p.SuccessRate >= 0.8)
                };
            }
        }

        public void CleanupOldData(int daysToKeep = 30)
        {
            lock (_lock)
            {
                var cutoffDate = DateTime.UtcNow.AddDays(-daysToKeep);
                
                // Clean traces
                var originalCount = _traces.Count;
                _traces = _traces.Where(t => t.Timestamp > cutoffDate).ToList();
                
                // Rewrite traces file
                if (_traces.Count != originalCount)
                {
                    var lines = _traces.Select(t => JsonSerializer.Serialize(t));
                    File.WriteAllLines(_tracesFile, lines);
                }

                // Clean unused patterns
                _patterns = _patterns.Where(p => p.LastUsed > cutoffDate).ToList();
                
                // Save patterns
                var json = JsonSerializer.Serialize(_patterns, new JsonSerializerOptions { WriteIndented = true });
                File.WriteAllText(_patternsFile, json);
            }
        }
    }
}
