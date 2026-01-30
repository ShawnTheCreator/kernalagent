using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace Kernel_Agent.Services
{
    public sealed class SecurityPolicyService
    {
        private static SecurityPolicyService? _instance;
        public static SecurityPolicyService Instance => _instance ??= new SecurityPolicyService();

        private readonly string _policyFilePath;
        private readonly object _lock = new();

        public event Action? PolicyChanged;

        public List<RestrictedAppRule> RestrictedApps { get; private set; } = new();

        public bool AutoBlurPasswordFieldsInMemory { get; set; } = true;
        public bool ScrubCreditCardNumbersFromLogs { get; set; } = true;
        public bool EnableHumanInTheLoopForPayments { get; set; } = true;
        public bool LogKeyboardInputDuringActiveTasks { get; set; } = false;

        private SecurityPolicyService()
        {
            var appDataPath = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var appFolder = Path.Combine(appDataPath, "KernelAgent");
            Directory.CreateDirectory(appFolder);
            _policyFilePath = Path.Combine(appFolder, "security_policy.json");

            Load();
        }

        public void Load()
        {
            lock (_lock)
            {
                try
                {
                    if (!File.Exists(_policyFilePath))
                    {
                        ResetToDefaultsInternal(save: true);
                        return;
                    }

                    var json = File.ReadAllText(_policyFilePath);
                    var dto = JsonSerializer.Deserialize<SecurityPolicyDto>(json, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });

                    if (dto == null)
                    {
                        ResetToDefaultsInternal(save: true);
                        return;
                    }

                    RestrictedApps = dto.RestrictedApps ?? new List<RestrictedAppRule>();

                    AutoBlurPasswordFieldsInMemory = dto.AutoBlurPasswordFieldsInMemory;
                    ScrubCreditCardNumbersFromLogs = dto.ScrubCreditCardNumbersFromLogs;
                    EnableHumanInTheLoopForPayments = dto.EnableHumanInTheLoopForPayments;
                    LogKeyboardInputDuringActiveTasks = dto.LogKeyboardInputDuringActiveTasks;

                    if (RestrictedApps.Count == 0)
                    {
                        SeedDefaults();
                        Save();
                    }
                }
                catch
                {
                    ResetToDefaultsInternal(save: true);
                }
            }

            PolicyChanged?.Invoke();
        }

        public void Save()
        {
            lock (_lock)
            {
                var dto = new SecurityPolicyDto
                {
                    RestrictedApps = RestrictedApps,
                    AutoBlurPasswordFieldsInMemory = AutoBlurPasswordFieldsInMemory,
                    ScrubCreditCardNumbersFromLogs = ScrubCreditCardNumbersFromLogs,
                    EnableHumanInTheLoopForPayments = EnableHumanInTheLoopForPayments,
                    LogKeyboardInputDuringActiveTasks = LogKeyboardInputDuringActiveTasks
                };

                var json = JsonSerializer.Serialize(dto, new JsonSerializerOptions
                {
                    WriteIndented = true
                });

                File.WriteAllText(_policyFilePath, json);
            }

            PolicyChanged?.Invoke();
        }

        public void ResetToDefaults()
        {
            lock (_lock)
            {
                ResetToDefaultsInternal(save: true);
            }

            PolicyChanged?.Invoke();
        }

        private void ResetToDefaultsInternal(bool save)
        {
            AutoBlurPasswordFieldsInMemory = true;
            ScrubCreditCardNumbersFromLogs = true;
            EnableHumanInTheLoopForPayments = true;
            LogKeyboardInputDuringActiveTasks = false;

            SeedDefaults();

            if (save)
            {
                Save();
            }
        }

        private void SeedDefaults()
        {
            RestrictedApps = new List<RestrictedAppRule>
            {
                new RestrictedAppRule { Id = "banking", DisplayName = "Banking (Chrome/Edge Tabs)", ProcessNameContains = "chrome", WindowTitleContains = "bank", IsEnabled = true },
                new RestrictedAppRule { Id = "password_manager", DisplayName = "Password Managers", ProcessNameContains = "bitwarden", WindowTitleContains = "password", IsEnabled = true },
                new RestrictedAppRule { Id = "private_messaging", DisplayName = "Private Messaging (Slack/Discord)", ProcessNameContains = "slack", WindowTitleContains = "", IsEnabled = false },
                new RestrictedAppRule { Id = "private_messaging_discord", DisplayName = "Private Messaging (Discord)", ProcessNameContains = "discord", WindowTitleContains = "", IsEnabled = false }
            };
        }

        public void AddRestrictedApp(string displayName, string processNameContains, string windowTitleContains, bool enabled = true)
        {
            lock (_lock)
            {
                var id = Guid.NewGuid().ToString("N");
                RestrictedApps.Add(new RestrictedAppRule
                {
                    Id = id,
                    DisplayName = displayName,
                    ProcessNameContains = processNameContains,
                    WindowTitleContains = windowTitleContains,
                    IsEnabled = enabled
                });

                Save();
            }
        }

        public void SetRuleEnabled(string ruleId, bool isEnabled)
        {
            lock (_lock)
            {
                var rule = RestrictedApps.FirstOrDefault(r => string.Equals(r.Id, ruleId, StringComparison.OrdinalIgnoreCase));
                if (rule == null) return;
                rule.IsEnabled = isEnabled;
                Save();
            }
        }

        public bool IsBlockedTargetApp(string? exeOrProcessName)
        {
            if (string.IsNullOrWhiteSpace(exeOrProcessName)) return false;

            var raw = exeOrProcessName.Trim();
            var proc = raw.EndsWith(".exe", StringComparison.OrdinalIgnoreCase) ? raw[..^4] : raw;
            proc = proc.ToLowerInvariant();

            lock (_lock)
            {
                foreach (var rule in RestrictedApps)
                {
                    if (!rule.IsEnabled) continue;
                    if (!string.IsNullOrWhiteSpace(rule.ProcessNameContains) && proc.Contains(rule.ProcessNameContains.ToLowerInvariant()))
                    {
                        return true;
                    }
                }
            }

            return false;
        }

        public GuardrailDecision EvaluateCurrentContext(ContextManager context)
        {
            try
            {
                context.RefreshContext();
                var process = context.ActiveProcessName ?? "";
                var title = context.ActiveWindowTitle ?? "";

                lock (_lock)
                {
                    foreach (var rule in RestrictedApps)
                    {
                        if (!rule.IsEnabled) continue;

                        var matchProcess = !string.IsNullOrWhiteSpace(rule.ProcessNameContains) &&
                                           process.Contains(rule.ProcessNameContains.Trim().ToLowerInvariant());

                        var matchTitle = !string.IsNullOrWhiteSpace(rule.WindowTitleContains) &&
                                         title.IndexOf(rule.WindowTitleContains.Trim(), StringComparison.OrdinalIgnoreCase) >= 0;

                        if (matchProcess || matchTitle)
                        {
                            return new GuardrailDecision
                            {
                                IsAllowed = false,
                                Reason = $"Security Vault blocked automation due to: {rule.DisplayName}",
                                MatchedRuleId = rule.Id,
                                MatchedRuleName = rule.DisplayName
                            };
                        }
                    }
                }

                return new GuardrailDecision { IsAllowed = true };
            }
            catch (Exception ex)
            {
                return new GuardrailDecision { IsAllowed = true, Reason = ex.Message };
            }
        }

        private sealed class SecurityPolicyDto
        {
            public List<RestrictedAppRule>? RestrictedApps { get; set; }

            public bool AutoBlurPasswordFieldsInMemory { get; set; } = true;
            public bool ScrubCreditCardNumbersFromLogs { get; set; } = true;
            public bool EnableHumanInTheLoopForPayments { get; set; } = true;
            public bool LogKeyboardInputDuringActiveTasks { get; set; } = false;
        }
    }

    public sealed class RestrictedAppRule
    {
        public string Id { get; set; } = "";
        public string DisplayName { get; set; } = "";
        public string ProcessNameContains { get; set; } = "";
        public string WindowTitleContains { get; set; } = "";
        public bool IsEnabled { get; set; } = true;
    }

    public sealed class GuardrailDecision
    {
        public bool IsAllowed { get; set; }
        public string? Reason { get; set; }
        public string? MatchedRuleId { get; set; }
        public string? MatchedRuleName { get; set; }
    }
}
