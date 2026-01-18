using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// ContextManager - Tracks the current environment context for intelligent command resolution.
    /// 
    /// Enables commands like:
    /// - "save this" → knows current app, calls appropriate save action
    /// - "make it bigger" → knows if referring to font, window, or zoom
    /// - "copy that" → knows what "that" refers to from recent actions
    /// </summary>
    public class ContextManager
    {
        // Singleton instance
        private static ContextManager? _instance;
        public static ContextManager Instance => _instance ??= new ContextManager();
        
        // Win32 API imports
        [DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();
        
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
        
        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
        
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
        
        // ===== CURRENT CONTEXT STATE =====
        
        /// <summary>Current foreground window title</summary>
        public string ActiveWindowTitle { get; private set; } = "";
        
        /// <summary>Current foreground app process name</summary>
        public string ActiveProcessName { get; private set; } = "";
        
        /// <summary>Current foreground app type (browser, editor, media, etc.)</summary>
        public AppType ActiveAppType { get; private set; } = AppType.Unknown;
        
        /// <summary>Current clipboard text content</summary>
        public string ClipboardText { get; private set; } = "";
        
        /// <summary>Last selected/highlighted text (if any)</summary>
        public string SelectedText { get; private set; } = "";
        
        /// <summary>Last action performed</summary>
        public string LastAction { get; private set; } = "";
        
        /// <summary>Last target of action</summary>
        public string LastTarget { get; private set; } = "";
        
        /// <summary>Timestamp of last context update</summary>
        public DateTime LastUpdated { get; private set; } = DateTime.MinValue;
        
        // ===== APP TYPE CLASSIFICATION =====
        
        public enum AppType
        {
            Unknown,
            Browser,
            TextEditor,
            CodeEditor,
            MediaPlayer,
            FileExplorer,
            Office,
            Terminal,
            ImageEditor,
            Messaging,
            System
        }
        
        // App name to type mappings
        private static readonly System.Collections.Generic.Dictionary<string, AppType> AppTypeMap = new()
        {
            // Browsers
            { "chrome", AppType.Browser },
            { "msedge", AppType.Browser },
            { "firefox", AppType.Browser },
            { "opera", AppType.Browser },
            { "brave", AppType.Browser },
            { "vivaldi", AppType.Browser },
            
            // Text Editors
            { "notepad", AppType.TextEditor },
            { "notepad++", AppType.TextEditor },
            { "wordpad", AppType.TextEditor },
            
            // Code Editors
            { "code", AppType.CodeEditor },
            { "devenv", AppType.CodeEditor },
            { "rider", AppType.CodeEditor },
            { "webstorm", AppType.CodeEditor },
            { "pycharm", AppType.CodeEditor },
            { "sublime_text", AppType.CodeEditor },
            { "atom", AppType.CodeEditor },
            
            // Media Players
            { "spotify", AppType.MediaPlayer },
            { "vlc", AppType.MediaPlayer },
            { "wmplayer", AppType.MediaPlayer },
            { "itunes", AppType.MediaPlayer },
            
            // File Explorer
            { "explorer", AppType.FileExplorer },
            
            // Office
            { "winword", AppType.Office },
            { "excel", AppType.Office },
            { "powerpnt", AppType.Office },
            { "onenote", AppType.Office },
            { "outlook", AppType.Office },
            
            // Terminal
            { "cmd", AppType.Terminal },
            { "powershell", AppType.Terminal },
            { "windowsterminal", AppType.Terminal },
            { "wt", AppType.Terminal },
            
            // Image Editors
            { "mspaint", AppType.ImageEditor },
            { "photoshop", AppType.ImageEditor },
            { "gimp", AppType.ImageEditor },
            
            // Messaging
            { "teams", AppType.Messaging },
            { "slack", AppType.Messaging },
            { "discord", AppType.Messaging },
            { "whatsapp", AppType.Messaging },
            { "telegram", AppType.Messaging },
        };
        
        // ===== PUBLIC METHODS =====
        
        /// <summary>
        /// Refresh all context information from the current environment.
        /// Should be called before processing a command.
        /// </summary>
        public void RefreshContext()
        {
            Debug.WriteLine("[CONTEXT] Refreshing context...");
            
            try
            {
                // Get active window info
                IntPtr hwnd = GetForegroundWindow();
                if (hwnd != IntPtr.Zero)
                {
                    // Window title
                    var titleBuilder = new StringBuilder(256);
                    GetWindowText(hwnd, titleBuilder, 256);
                    ActiveWindowTitle = titleBuilder.ToString();
                    
                    // Process name
                    GetWindowThreadProcessId(hwnd, out uint processId);
                    try
                    {
                        var process = Process.GetProcessById((int)processId);
                        ActiveProcessName = process.ProcessName.ToLower();
                    }
                    catch
                    {
                        ActiveProcessName = "";
                    }
                    
                    // Classify app type
                    ActiveAppType = ClassifyApp(ActiveProcessName);
                }
                
                // Get clipboard content
                try
                {
                    if (Clipboard.ContainsText())
                    {
                        ClipboardText = Clipboard.GetText();
                        if (ClipboardText.Length > 500)
                            ClipboardText = ClipboardText.Substring(0, 500) + "...";
                    }
                    else
                    {
                        ClipboardText = "";
                    }
                }
                catch
                {
                    ClipboardText = "";
                }
                
                LastUpdated = DateTime.Now;
                
                Debug.WriteLine($"[CONTEXT] Window: '{ActiveWindowTitle}'");
                Debug.WriteLine($"[CONTEXT] Process: {ActiveProcessName} ({ActiveAppType})");
                Debug.WriteLine($"[CONTEXT] Clipboard: {ClipboardText.Length} chars");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[CONTEXT] Error refreshing: {ex.Message}");
            }
        }
        
        /// <summary>
        /// Record an action that was just performed.
        /// Used for contextual commands like "do that again".
        /// </summary>
        public void RecordAction(string action, string target)
        {
            LastAction = action;
            LastTarget = target;
            Debug.WriteLine($"[CONTEXT] Recorded action: {action} -> {target}");
        }
        
        /// <summary>
        /// Try to capture currently selected text.
        /// Uses Ctrl+C and reads clipboard (with rollback).
        /// </summary>
        public string CaptureSelectedText()
        {
            try
            {
                // Save current clipboard
                string originalClipboard = "";
                if (Clipboard.ContainsText())
                    originalClipboard = Clipboard.GetText();
                
                // Try to copy selection
                SendKeys.SendWait("^c");
                Thread.Sleep(100);
                
                // Read new clipboard
                if (Clipboard.ContainsText())
                {
                    SelectedText = Clipboard.GetText();
                }
                
                // Restore original clipboard
                if (!string.IsNullOrEmpty(originalClipboard))
                {
                    Clipboard.SetText(originalClipboard);
                }
                
                Debug.WriteLine($"[CONTEXT] Captured selection: '{SelectedText}'");
                return SelectedText;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[CONTEXT] Error capturing selection: {ex.Message}");
                return "";
            }
        }
        
        /// <summary>
        /// Get context as a dictionary for sending to LLM.
        /// </summary>
        public System.Collections.Generic.Dictionary<string, object> GetContextDict()
        {
            return new System.Collections.Generic.Dictionary<string, object>
            {
                { "active_window", ActiveWindowTitle },
                { "active_app", ActiveProcessName },
                { "app_type", ActiveAppType.ToString().ToLower() },
                { "clipboard", ClipboardText.Length > 100 ? ClipboardText.Substring(0, 100) + "..." : ClipboardText },
                { "selected_text", SelectedText },
                { "last_action", LastAction },
                { "last_target", LastTarget },
            };
        }
        
        /// <summary>
        /// Get a concise context summary string for LLM prompt.
        /// </summary>
        public string GetContextSummary()
        {
            RefreshContext();
            
            var sb = new StringBuilder();
            sb.AppendLine($"Active App: {ActiveProcessName} ({ActiveAppType})");
            sb.AppendLine($"Window: {ActiveWindowTitle}");
            
            if (!string.IsNullOrEmpty(SelectedText))
                sb.AppendLine($"Selected: \"{TruncateText(SelectedText, 50)}\"");
            
            if (!string.IsNullOrEmpty(ClipboardText))
                sb.AppendLine($"Clipboard: \"{TruncateText(ClipboardText, 50)}\"");
            
            if (!string.IsNullOrEmpty(LastAction))
                sb.AppendLine($"Last action: {LastAction} on {LastTarget}");
            
            return sb.ToString();
        }
        
        // ===== CONTEXT-AWARE COMMAND RESOLUTION =====
        
        /// <summary>
        /// Resolve "this" in commands like "save this", "close this".
        /// Returns the inferred target based on context.
        /// </summary>
        public string ResolveThis()
        {
            // "this" typically refers to the current window/app
            return ActiveProcessName;
        }
        
        /// <summary>
        /// Resolve "it" in commands like "make it bigger", "send it".
        /// </summary>
        public string ResolveIt()
        {
            // "it" could refer to: selection, last target, or current app
            if (!string.IsNullOrEmpty(SelectedText))
                return SelectedText;
            if (!string.IsNullOrEmpty(LastTarget))
                return LastTarget;
            return ActiveProcessName;
        }
        
        /// <summary>
        /// Resolve "that" in commands like "copy that", "do that again".
        /// </summary>
        public string ResolveThat()
        {
            // "that" typically refers to the last action target
            return !string.IsNullOrEmpty(LastTarget) ? LastTarget : SelectedText;
        }
        
        /// <summary>
        /// Infer what "bigger" means based on context.
        /// </summary>
        public string ResolveBigger()
        {
            return ActiveAppType switch
            {
                AppType.Browser => "zoom_in",      // Browser zoom
                AppType.TextEditor => "font_size_increase",
                AppType.CodeEditor => "font_size_increase",
                AppType.ImageEditor => "zoom_in",
                AppType.MediaPlayer => "volume_up",
                _ => "maximize_window"  // Default: maximize window
            };
        }
        
        /// <summary>
        /// Infer what "smaller" means based on context.
        /// </summary>
        public string ResolveSmaller()
        {
            return ActiveAppType switch
            {
                AppType.Browser => "zoom_out",
                AppType.TextEditor => "font_size_decrease",
                AppType.CodeEditor => "font_size_decrease",
                AppType.ImageEditor => "zoom_out",
                AppType.MediaPlayer => "volume_down",
                _ => "minimize_window"
            };
        }
        
        /// <summary>
        /// Get appropriate save action for current app.
        /// </summary>
        public string GetSaveAction()
        {
            // All apps use Ctrl+S
            return "save";
        }
        
        // ===== PRIVATE HELPERS =====
        
        private AppType ClassifyApp(string processName)
        {
            if (string.IsNullOrEmpty(processName))
                return AppType.Unknown;
            
            string name = processName.ToLower().Replace(".exe", "");
            
            if (AppTypeMap.TryGetValue(name, out AppType type))
                return type;
            
            // Try partial match
            foreach (var kvp in AppTypeMap)
            {
                if (name.Contains(kvp.Key))
                    return kvp.Value;
            }
            
            return AppType.Unknown;
        }
        
        private string TruncateText(string text, int maxLength)
        {
            if (string.IsNullOrEmpty(text)) return "";
            return text.Length <= maxLength ? text : text.Substring(0, maxLength) + "...";
        }
    }
}
