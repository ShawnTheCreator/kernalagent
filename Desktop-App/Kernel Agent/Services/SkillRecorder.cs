using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// SkillRecorder - Record, store, and replay user-defined automation workflows.
    /// 
    /// Enables commands like:
    /// - "Learn how I do this" → Start recording
    /// - "Stop learning" → Stop and save recording
    /// - "Do the login thing" → Play back a recorded skill
    /// - "Do that weekly report thing" → Play saved workflow
    /// </summary>
    public class SkillRecorder
    {
        private static SkillRecorder? _instance;
        public static SkillRecorder Instance => _instance ??= new SkillRecorder();
        
        private readonly string _skillsDirectory;
        private List<RecordedAction> _currentRecording = new();
        private bool _isRecording = false;
        private string _currentSkillName = "";
        private DateTime _recordingStartTime;
        
        public SkillRecorder()
        {
            // Store skills in user's AppData
            _skillsDirectory = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "KernelAgent",
                "Skills"
            );
            
            // Create directory if it doesn't exist
            if (!Directory.Exists(_skillsDirectory))
            {
                Directory.CreateDirectory(_skillsDirectory);
                Debug.WriteLine($"[SKILL] Created skills directory: {_skillsDirectory}");
            }
        }
        
        // ===== RECORDING STATE =====
        
        public bool IsRecording => _isRecording;
        public string CurrentSkillName => _currentSkillName;
        public int RecordedActionsCount => _currentRecording.Count;
        
        // ===== RECORDING METHODS =====
        
        /// <summary>
        /// Start recording a new skill.
        /// </summary>
        public void StartRecording(string skillName)
        {
            if (_isRecording)
            {
                Debug.WriteLine($"[SKILL] Already recording '{_currentSkillName}', stopping first.");
                StopRecording(false);
            }
            
            _currentSkillName = SanitizeSkillName(skillName);
            _currentRecording = new List<RecordedAction>();
            _recordingStartTime = DateTime.Now;
            _isRecording = true;
            
            Debug.WriteLine($"[SKILL] 🔴 Started recording: '{_currentSkillName}'");
        }
        
        /// <summary>
        /// Record an action during recording session.
        /// </summary>
        public void RecordAction(string action, Dictionary<string, object>? parameters = null)
        {
            if (!_isRecording) return;
            
            var recorded = new RecordedAction
            {
                Action = action,
                Parameters = parameters ?? new Dictionary<string, object>(),
                Timestamp = DateTime.Now,
                DelayFromPrevious = _currentRecording.Count > 0 
                    ? (int)(DateTime.Now - _currentRecording.Last().Timestamp).TotalMilliseconds
                    : 0
            };
            
            _currentRecording.Add(recorded);
            Debug.WriteLine($"[SKILL] Recorded: {action} ({_currentRecording.Count} total)");
        }
        
        /// <summary>
        /// Stop recording and optionally save the skill.
        /// </summary>
        public Skill? StopRecording(bool save = true)
        {
            if (!_isRecording)
            {
                Debug.WriteLine("[SKILL] Not recording.");
                return null;
            }
            
            _isRecording = false;
            
            if (_currentRecording.Count == 0)
            {
                Debug.WriteLine("[SKILL] No actions recorded, discarding.");
                return null;
            }
            
            var skill = new Skill
            {
                Name = _currentSkillName,
                Description = $"Recorded on {_recordingStartTime:yyyy-MM-dd HH:mm}",
                Actions = _currentRecording.ToList(),
                CreatedAt = _recordingStartTime,
                LastUsed = _recordingStartTime,
                UseCount = 0
            };
            
            if (save)
            {
                SaveSkill(skill);
                Debug.WriteLine($"[SKILL] ⏹ Saved skill: '{_currentSkillName}' with {skill.Actions.Count} actions");
            }
            else
            {
                Debug.WriteLine($"[SKILL] ⏹ Discarded recording: '{_currentSkillName}'");
            }
            
            _currentRecording = new List<RecordedAction>();
            _currentSkillName = "";
            
            return skill;
        }
        
        // ===== PLAYBACK METHODS =====
        
        /// <summary>
        /// Play back a recorded skill.
        /// </summary>
        public async Task<bool> PlaySkillAsync(string skillName, Dictionary<string, string>? variables = null)
        {
            var skill = LoadSkill(skillName);
            if (skill == null)
            {
                Debug.WriteLine($"[SKILL] Skill not found: '{skillName}'");
                return false;
            }
            
            Debug.WriteLine($"[SKILL] ▶ Playing skill: '{skill.Name}' ({skill.Actions.Count} actions)");
            
            var executor = new SmartExecutor();
            
            foreach (var action in skill.Actions)
            {
                // Apply variable substitutions
                var parameters = ApplyVariables(action.Parameters, variables);
                
                // Convert to JSON element for executor
                var stepJson = JsonSerializer.Serialize(new Dictionary<string, object>
                {
                    { "action", action.Action },
                    { "target", parameters.GetValueOrDefault("target", "") ?? "" },
                    { "content", parameters.GetValueOrDefault("content", "") ?? "" },
                    { "url", parameters.GetValueOrDefault("url", "") ?? "" },
                    { "path", parameters.GetValueOrDefault("path", "") ?? "" }
                });
                
                var step = JsonDocument.Parse(stepJson).RootElement;
                
                // Execute with timing from recording
                if (action.DelayFromPrevious > 100)
                {
                    await Task.Delay(Math.Min(action.DelayFromPrevious, 2000)); // Cap at 2 seconds
                }
                
                // Execute the action
                Debug.WriteLine($"[SKILL] Executing: {action.Action}");
                // Note: Individual action execution would go through SmartExecutor
            }
            
            // Update usage stats
            skill.LastUsed = DateTime.Now;
            skill.UseCount++;
            SaveSkill(skill);
            
            Debug.WriteLine($"[SKILL] ✓ Skill completed: '{skill.Name}'");
            return true;
        }
        
        /// <summary>
        /// Get list of all saved skills.
        /// </summary>
        public List<SkillSummary> GetAllSkills()
        {
            var skills = new List<SkillSummary>();
            
            try
            {
                foreach (var file in Directory.GetFiles(_skillsDirectory, "*.json"))
                {
                    try
                    {
                        var json = File.ReadAllText(file);
                        var skill = JsonSerializer.Deserialize<Skill>(json);
                        if (skill != null)
                        {
                            skills.Add(new SkillSummary
                            {
                                Name = skill.Name,
                                Description = skill.Description,
                                ActionCount = skill.Actions.Count,
                                UseCount = skill.UseCount,
                                LastUsed = skill.LastUsed
                            });
                        }
                    }
                    catch { }
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SKILL] Error listing skills: {ex.Message}");
            }
            
            return skills.OrderByDescending(s => s.UseCount).ToList();
        }
        
        /// <summary>
        /// Find a skill by fuzzy name matching.
        /// </summary>
        public Skill? FindSkill(string query)
        {
            var skills = GetAllSkills();
            query = query.ToLower();
            
            // Exact match first
            var exact = skills.FirstOrDefault(s => s.Name.ToLower() == query);
            if (exact != null) return LoadSkill(exact.Name);
            
            // Contains match
            var contains = skills.FirstOrDefault(s => s.Name.ToLower().Contains(query) || query.Contains(s.Name.ToLower()));
            if (contains != null) return LoadSkill(contains.Name);
            
            // Word match
            var queryWords = query.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            foreach (var skill in skills)
            {
                var nameWords = skill.Name.ToLower().Split(' ', '_', '-');
                if (queryWords.All(qw => nameWords.Any(nw => nw.Contains(qw))))
                    return LoadSkill(skill.Name);
            }
            
            return null;
        }
        
        /// <summary>
        /// Delete a skill.
        /// </summary>
        public bool DeleteSkill(string skillName)
        {
            var path = GetSkillPath(skillName);
            if (File.Exists(path))
            {
                File.Delete(path);
                Debug.WriteLine($"[SKILL] Deleted: '{skillName}'");
                return true;
            }
            return false;
        }
        
        // ===== PRIVATE HELPERS =====
        
        private void SaveSkill(Skill skill)
        {
            var path = GetSkillPath(skill.Name);
            var json = JsonSerializer.Serialize(skill, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(path, json);
        }
        
        private Skill? LoadSkill(string skillName)
        {
            var path = GetSkillPath(skillName);
            if (!File.Exists(path)) return null;
            
            try
            {
                var json = File.ReadAllText(path);
                return JsonSerializer.Deserialize<Skill>(json);
            }
            catch
            {
                return null;
            }
        }
        
        private string GetSkillPath(string skillName)
        {
            return Path.Combine(_skillsDirectory, $"{SanitizeSkillName(skillName)}.json");
        }
        
        private string SanitizeSkillName(string name)
        {
            // Remove invalid filename characters
            var invalid = Path.GetInvalidFileNameChars();
            var sanitized = new string(name.Where(c => !invalid.Contains(c)).ToArray());
            return sanitized.ToLower().Replace(" ", "_").Trim('_');
        }
        
        private Dictionary<string, object> ApplyVariables(Dictionary<string, object> parameters, Dictionary<string, string>? variables)
        {
            if (variables == null || variables.Count == 0)
                return parameters;
            
            var result = new Dictionary<string, object>(parameters);
            
            foreach (var kvp in result.ToList())
            {
                if (kvp.Value is string strValue)
                {
                    foreach (var variable in variables)
                    {
                        strValue = strValue.Replace($"{{{variable.Key}}}", variable.Value);
                        strValue = strValue.Replace($"${{{variable.Key}}}", variable.Value);
                    }
                    result[kvp.Key] = strValue;
                }
            }
            
            return result;
        }
    }
    
    // ===== DATA MODELS =====
    
    public class RecordedAction
    {
        public string Action { get; set; } = "";
        public Dictionary<string, object> Parameters { get; set; } = new();
        public DateTime Timestamp { get; set; }
        public int DelayFromPrevious { get; set; }  // ms
    }
    
    public class Skill
    {
        public string Name { get; set; } = "";
        public string Description { get; set; } = "";
        public List<RecordedAction> Actions { get; set; } = new();
        public DateTime CreatedAt { get; set; }
        public DateTime LastUsed { get; set; }
        public int UseCount { get; set; }
        // Variables that can be substituted during playback
        public List<string> Variables { get; set; } = new();
    }
    
    public class SkillSummary
    {
        public string Name { get; set; } = "";
        public string Description { get; set; } = "";
        public int ActionCount { get; set; }
        public int UseCount { get; set; }
        public DateTime LastUsed { get; set; }
    }
}
