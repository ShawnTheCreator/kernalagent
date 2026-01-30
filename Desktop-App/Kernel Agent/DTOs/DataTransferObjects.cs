using System;
using System.Collections.Generic;

namespace Kernel_Agent.DTOs
{
    // Timeline Event DTO for History page
    public class TimelineEventDto
    {
        public string Id { get; set; } = string.Empty;
        public string Type { get; set; } = string.Empty; // chat_user, chat_agent, action_tool, memory_thought
        public string Content { get; set; } = string.Empty;
        public Dictionary<string, object>? Metadata { get; set; }
        public string Timestamp { get; set; } = string.Empty;
        public string? SessionId { get; set; }
        
        [System.Text.Json.Serialization.JsonIgnore]
        public DateTime TimestampDt
        {
            get
            {
                if (DateTime.TryParse(Timestamp, out var dt)) return dt;
                return DateTime.MinValue;
            }
        }

        [System.Text.Json.Serialization.JsonIgnore]
        public string FormattedTime => TimestampDt.ToString("HH:mm");
        
        [System.Text.Json.Serialization.JsonIgnore]
        public Microsoft.UI.Xaml.Media.SolidColorBrush DisplayColor
        {
            get
            {
                // Simple color mapping logic
                byte a = 255; byte r = 255; byte g = 255; byte b = 255;
                
                switch (Type)
                {
                    case "chat_agent": // #FF34A853 (Green)
                        r = 52; g = 168; b = 83;
                        break;
                    case "action_tool": // #FF4285F4 (Blue)
                        r = 66; g = 133; b = 244;
                        break;
                    case "memory_thought": // #FFAAAAAA (Gray)
                        r = 170; g = 170; b = 170;
                        break;
                    case "chat_user": // White
                    default: 
                        r = 255; g = 255; b = 255;
                        break;
                }
                
                return new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(a, r, g, b));
            }
        }
    }

    // Skill DTO for Memory page
    public class SkillDto
    {
        public string Id { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        
        [System.Text.Json.Serialization.JsonPropertyName("intent_signature")]
        public string IntentSignature { get; set; } = string.Empty;
        
        public string? Description { get; set; }
        public float Confidence { get; set; }
        
        [System.Text.Json.Serialization.JsonPropertyName("success_count")]
        public int SuccessCount { get; set; }
        
        [System.Text.Json.Serialization.JsonPropertyName("failure_count")]
        public int FailureCount { get; set; }
        
        [System.Text.Json.Serialization.JsonPropertyName("last_used_at")]
        public string? LastUsedAt { get; set; }
        
        [System.Text.Json.Serialization.JsonPropertyName("created_at")]
        public string? CreatedAt { get; set; }
    }

    // Session DTO for data tracking
    public class SessionDto
    {
        [System.Text.Json.Serialization.JsonPropertyName("session_id")]
        public string SessionId { get; set; } = string.Empty;
        
        public string Intent { get; set; } = string.Empty;
        
        [System.Text.Json.Serialization.JsonPropertyName("started_at")]
        public string StartedAt { get; set; } = string.Empty;
        
        [System.Text.Json.Serialization.JsonPropertyName("ended_at")]
        public string? EndedAt { get; set; }
        
        public string Status { get; set; } = string.Empty;
        public float Confidence { get; set; }
        
        [System.Text.Json.Serialization.JsonPropertyName("step_count")]
        public int StepCount { get; set; }
        
        // Legacy properties for compatibility
        public DateTime StartTime => DateTime.TryParse(StartedAt, out var dt) ? dt : DateTime.MinValue;
        public DateTime? EndTime => DateTime.TryParse(EndedAt, out var dt) ? dt : null;
        public int TaskCount => StepCount;
        public double SuccessRate { get; set; }
        public string? UpdatedAt { get; set; }
    }

    // Dashboard Stats DTO
    public class DashboardStatsDto
    {
        public int TotalTasks { get; set; }
        public double SuccessRate { get; set; }
        public int AverageLatency { get; set; }
        public string Uptime { get; set; } = string.Empty;
        public int ActiveSkills { get; set; }
        
        // Legacy property for compatibility
        public int SessionsToday { get; set; }
    }

    // Activity DTO for timeline
    public class ActivityDto
    {
        public string? Id { get; set; }
        public string? State { get; set; }
        public string? Title { get; set; }
        public string? Description { get; set; }
        public DateTime Timestamp { get; set; }
        public bool IsNew { get; set; }
    }

    // Metrics DTO for dashboard
    public class MetricsDto
    {
        public int[]? TasksPerHour { get; set; }
        public int[]? LatencyMs { get; set; }
        public int[]? SuccessRate { get; set; }
    }

    // Memory DTO for cognitive tracking
    public class MemoryDto
    {
        [System.Text.Json.Serialization.JsonPropertyName("frequent_skills")]
        public List<string> FrequentSkills { get; set; } = new();
        
        [System.Text.Json.Serialization.JsonPropertyName("failure_patterns")]
        public List<string> FailurePatterns { get; set; } = new();
        
        [System.Text.Json.Serialization.JsonPropertyName("success_patterns")]
        public List<string> SuccessPatterns { get; set; } = new();
        
        [System.Text.Json.Serialization.JsonPropertyName("updated_at")]
        public string? UpdatedAt { get; set; }
        
        // Legacy properties for compatibility
        public List<SkillDto> FrequentSkillsObjects => new(); // Convert string list to objects if needed
        public List<ActivityDto> RecentActivities { get; set; } = new();
        public MetricsDto? PerformanceMetrics { get; set; }
        public DateTime LastUpdated => DateTime.TryParse(UpdatedAt, out var dt) ? dt : DateTime.MinValue;
    }

    // Timeline Response wrapper
    public class TimelineResponse
    {
        public List<TimelineEventDto> Events { get; set; } = new();
        public int Count { get; set; }
    }
}
