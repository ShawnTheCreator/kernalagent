using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Kernel_Agent.Services;

namespace Kernel_Agent.Kernel
{
    public sealed class KernelOrchestrator
    {
        public static KernelOrchestrator Instance { get; } = new KernelOrchestrator();
        private readonly SafeMemoryLogger _logger;

        private KernelOrchestrator()
        {
            _logger = new SafeMemoryLogger();
        }

        public async Task<KernelRunResult> RunAsync(
            string command,
            SmartExecutor executor,
            Action<int, int, string, string>? onStepProgress
        )
        {
            var stopwatch = Stopwatch.StartNew();
            var trace = new ExecutionTrace { Command = command };

            try
            {
                if (string.IsNullOrWhiteSpace(command))
                {
                    return new KernelRunResult { AgentText = string.Empty };
                }

                System.Diagnostics.Debug.WriteLine($"[KERNEL] Interpret start: '{command}'");
                var interpretationJson = await ApiService.Instance.GetKernelInterpretationRawAsync(command);
                trace.Interpretation = interpretationJson;
                
                System.Diagnostics.Debug.WriteLine($"[KERNEL] Interpret done. Bytes={(interpretationJson ?? string.Empty).Length}");

                ExtractIntentAndEntities(interpretationJson ?? string.Empty, trace);

                if (string.IsNullOrWhiteSpace(interpretationJson))
                {
                    trace.Success = false;
                    trace.Error = "Failed to get interpretation";
                    await _logger.LogExecutionAsync(trace);
                    return new KernelRunResult { AgentText = string.Empty };
                }

                System.Diagnostics.Debug.WriteLine("[KERNEL] Plan start");
                var planJson = await ApiService.Instance.GetKernelPlanRawAsync(command, interpretationJson ?? "{}");
                trace.Plan = planJson;

                System.Diagnostics.Debug.WriteLine($"[KERNEL] Plan done. Bytes={(planJson ?? string.Empty).Length}");

                if (string.IsNullOrWhiteSpace(planJson))
                {
                    trace.Success = false;
                    trace.Error = "Failed to get plan";
                    await _logger.LogExecutionAsync(trace);
                    return new KernelRunResult { AgentText = string.Empty };
                }

                string? agentText = null;
                JsonElement? stepsArray = null;
                double? confidence = null;

                try
                {
                    using var doc = JsonDocument.Parse(planJson);
                    var root = doc.RootElement;

                    if (root.ValueKind == JsonValueKind.Object)
                    {
                        if (root.TryGetProperty("confidence", out var confEl) &&
                            confEl.ValueKind == JsonValueKind.Number &&
                            confEl.TryGetDouble(out var c))
                        {
                            confidence = c;
                        }

                        if (root.TryGetProperty("steps", out var stepsEl) &&
                            stepsEl.ValueKind == JsonValueKind.Array)
                        {
                            stepsArray = stepsEl.Clone();
                        }
                    }
                }
                catch
                {
                    trace.Success = false;
                    trace.Error = "Failed to parse plan JSON";
                    await _logger.LogExecutionAsync(trace);
                    return new KernelRunResult { AgentText = planJson };
                }

                if (stepsArray.HasValue)
                {
                    var stepsEl = stepsArray.Value;

                    if (stepsEl.GetArrayLength() == 1 &&
                        stepsEl[0].TryGetProperty("action", out var aEl) &&
                        string.Equals(aEl.GetString(), "conversation", StringComparison.OrdinalIgnoreCase))
                    {
                        var content = stepsEl[0].TryGetProperty("content", out var cEl) ? (cEl.GetString() ?? "") : "";
                        
                        trace.Success = true;
                        trace.Confidence = confidence;
                        trace.DurationMs = stopwatch.ElapsedMilliseconds;
                        await _logger.LogExecutionAsync(trace);
                        
                        return new KernelRunResult
                        {
                            AgentText = content,
                            WasConversation = true,
                            Confidence = confidence
                        };
                    }

                    executor.SetOriginalGoal(command);
                    executor.SetPlanConfidence(confidence);

                    var execResult = await executor.ExecutePlanAsync(stepsEl, onStepProgress);
                    
                    // Log execution steps
                    trace.Steps = execResult.ActionResults?.Select(s => new ExecutionStep
                    {
                        Action = s.Action,
                        Parameters = new Dictionary<string, object>(), // ActionResults doesn't have Parameters
                        Success = s.Success,
                        Error = s.Error,
                        DurationMs = 0 // ActionResults doesn't have timing
                    }).ToList() ?? new List<ExecutionStep>();

                    trace.Success = execResult.Success;
                    trace.Error = execResult.Error;
                    trace.Confidence = confidence;
                    trace.DurationMs = stopwatch.ElapsedMilliseconds;
                    await _logger.LogExecutionAsync(trace);

                    return new KernelRunResult
                    {
                        AgentText = agentText ?? planJson,
                        Confidence = confidence,
                        ExecutionSuccess = execResult.Success,
                        ExecutionError = execResult.Error
                    };
                }

                trace.Success = true;
                trace.Confidence = confidence;
                trace.DurationMs = stopwatch.ElapsedMilliseconds;
                await _logger.LogExecutionAsync(trace);

                return new KernelRunResult
                {
                    AgentText = agentText ?? planJson,
                    Confidence = confidence
                };
            }
            catch (Exception ex)
            {
                trace.Success = false;
                trace.Error = ex.Message;
                trace.DurationMs = stopwatch.ElapsedMilliseconds;
                await _logger.LogExecutionAsync(trace);
                
                return new KernelRunResult
                {
                    AgentText = $"Error: {ex.Message}",
                    ExecutionSuccess = false,
                    ExecutionError = ex.Message
                };
            }
        }

        private void ExtractIntentAndEntities(string interpretationJson, ExecutionTrace trace)
        {
            try
            {
                using var doc = JsonDocument.Parse(interpretationJson);
                var root = doc.RootElement;

                if (root.TryGetProperty("intent", out var intentEl))
                {
                    trace.Intent = intentEl.GetString() ?? "";
                }

                if (root.TryGetProperty("entities", out var entitiesEl) && entitiesEl.ValueKind == JsonValueKind.Array)
                {
                    trace.Entities = entitiesEl.EnumerateArray()
                        .Select(e => e.GetString())
                        .Where(s => !string.IsNullOrEmpty(s))
                        .ToList()!;
                }

                if (root.TryGetProperty("capabilities", out var capsEl) && capsEl.ValueKind == JsonValueKind.Array)
                {
                    trace.Capabilities = capsEl.EnumerateArray()
                        .Select(c => c.GetString())
                        .Where(s => !string.IsNullOrEmpty(s))
                        .ToList()!;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to extract intent/entities: {ex.Message}");
            }
        }
    }

    public sealed class KernelRunResult
    {
        public string? AgentText { get; set; }
        public bool WasConversation { get; set; }
        public double? Confidence { get; set; }
        public bool ExecutionSuccess { get; set; }
        public string? ExecutionError { get; set; }
    }
}
