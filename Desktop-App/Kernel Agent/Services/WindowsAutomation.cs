using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading;
using WindowsInput;

namespace Kernel_Agent.Services
{
    public class WindowsAutomation
    {
        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr hWnd);

        // Common app paths for Windows
        private static readonly Dictionary<string, string[]> AppPaths = new()
        {
            { "chrome.exe", new[] {
                @"C:\Program Files\Google\Chrome\Application\chrome.exe",
                @"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            }},
            { "msedge.exe", new[] {
                @"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                @"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            }},
            { "firefox.exe", new[] {
                @"C:\Program Files\Mozilla Firefox\firefox.exe",
                @"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
            }},
            { "code.exe", new[] {
                Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
                @"C:\Program Files\Microsoft VS Code\Code.exe"
            }},
            { "winword.exe", new[] {
                @"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
                @"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
                @"C:\Program Files\Microsoft Office\Office16\WINWORD.EXE"
            }},
            { "excel.exe", new[] {
                @"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
                @"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE"
            }},
            { "powerpnt.exe", new[] {
                @"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
                @"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE"
            }}
        };

        public void OpenApplication(string exeName)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opening: {exeName}");
                
                // Method 1: Try shell execute (handles .exe names that are registered)
                try
                {
                    var startInfo = new ProcessStartInfo
                    {
                        FileName = exeName,
                        UseShellExecute = true
                    };
                    Process.Start(startInfo);
                    System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opened via shell: {exeName}");
                    return;
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Shell execute failed: {ex.Message}");
                }

                // Method 2: Try known paths
                string lowerExe = exeName.ToLowerInvariant();
                if (AppPaths.TryGetValue(lowerExe, out var paths))
                {
                    foreach (var path in paths)
                    {
                        if (File.Exists(path))
                        {
                            Process.Start(new ProcessStartInfo
                            {
                                FileName = path,
                                UseShellExecute = true
                            });
                            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opened via path: {path}");
                            return;
                        }
                    }
                }

                // Method 3: Try "start" command (opens associated apps)
                try
                {
                    // Remove .exe for start command
                    string appName = exeName.Replace(".exe", "").Replace(".EXE", "");
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = "cmd.exe",
                        Arguments = $"/c start {appName}",
                        UseShellExecute = true,
                        CreateNoWindow = true
                    });
                    System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opened via start command: {appName}");
                    return;
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Start command failed: {ex.Message}");
                }

                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Could not find: {exeName}");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Error opening {exeName}: {ex.Message}");
            }
        }

        public void FocusWindow(string processName)
        {
            var process = Process.GetProcessesByName(processName).FirstOrDefault();
            if (process != null)
            {
                SetForegroundWindow(process.MainWindowHandle);
            }
        }

        public void TypeIntoApp(string text)
        {
            // Use SendKeys for basic text input as fallback
            System.Windows.Forms.SendKeys.SendWait(text);
        }

        public void OpenAndType(string exeName, string processName, string text)
        {
            OpenApplication(exeName);
            Thread.Sleep(2000); // Wait for app to open
            FocusWindow(processName);
            Thread.Sleep(500); // Wait for focus
            TypeIntoApp(text);
        }
    }
}

