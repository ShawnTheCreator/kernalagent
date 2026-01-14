using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading;
using System.Drawing;
using System.Drawing.Imaging;
using WindowsInput;

namespace Kernel_Agent.Services
{
    public class WindowsAutomation
    {
        // ===== Win32 API Imports =====
        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr hWnd);
        
        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        
        [DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();
        
        [DllImport("user32.dll")]
        private static extern bool LockWorkStation();
        
        [DllImport("user32.dll")]
        private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
        
        // Virtual Key Codes
        private const byte VK_VOLUME_UP = 0xAF;
        private const byte VK_VOLUME_DOWN = 0xAE;
        private const byte VK_VOLUME_MUTE = 0xAD;
        private const int KEYEVENTF_KEYUP = 0x0002;
        
        // ShowWindow commands
        private const int SW_MINIMIZE = 6;
        private const int SW_MAXIMIZE = 3;
        private const int SW_RESTORE = 9;

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

        // ===== OPEN APPLICATION =====
        public void OpenApplication(string exeName)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opening: {exeName}");
                
                // Method 1: Try shell execute
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
                            Process.Start(new ProcessStartInfo { FileName = path, UseShellExecute = true });
                            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opened via path: {path}");
                            return;
                        }
                    }
                }

                // Method 3: Try start command
                try
                {
                    string appName = exeName.Replace(".exe", "").Replace(".EXE", "");
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = "cmd.exe",
                        Arguments = $"/c start {appName}",
                        UseShellExecute = true,
                        CreateNoWindow = true
                    });
                    System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opened via start: {appName}");
                    return;
                }
                catch { }

                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Could not open: {exeName}");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Error opening {exeName}: {ex.Message}");
            }
        }

        // ===== CLOSE APPLICATION =====
        public void CloseApplication(string processName)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Closing: {processName}");
                var processes = Process.GetProcessesByName(processName);
                foreach (var process in processes)
                {
                    process.CloseMainWindow();
                    if (!process.WaitForExit(3000))
                    {
                        process.Kill();
                    }
                }
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Closed {processes.Length} instances of {processName}");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Error closing {processName}: {ex.Message}");
            }
        }

        // ===== VOLUME CONTROL =====
        public void VolumeUp(int amount = 1)
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Volume up x{amount}");
            for (int i = 0; i < amount; i++)
            {
                keybd_event(VK_VOLUME_UP, 0, 0, UIntPtr.Zero);
                keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            }
        }

        public void VolumeDown(int amount = 1)
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Volume down x{amount}");
            for (int i = 0; i < amount; i++)
            {
                keybd_event(VK_VOLUME_DOWN, 0, 0, UIntPtr.Zero);
                keybd_event(VK_VOLUME_DOWN, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            }
        }

        public void VolumeMute()
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Toggle mute");
            keybd_event(VK_VOLUME_MUTE, 0, 0, UIntPtr.Zero);
            keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        // ===== WINDOW MANAGEMENT =====
        public void MinimizeWindow()
        {
            var hwnd = GetForegroundWindow();
            ShowWindow(hwnd, SW_MINIMIZE);
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Window minimized");
        }

        public void MaximizeWindow()
        {
            var hwnd = GetForegroundWindow();
            ShowWindow(hwnd, SW_MAXIMIZE);
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Window maximized");
        }

        public void RestoreWindow()
        {
            var hwnd = GetForegroundWindow();
            ShowWindow(hwnd, SW_RESTORE);
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Window restored");
        }

        // ===== SYSTEM COMMANDS =====
        public void LockScreen()
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Locking screen");
            LockWorkStation();
        }

        public void Sleep()
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Sleep mode");
            Process.Start(new ProcessStartInfo
            {
                FileName = "rundll32.exe",
                Arguments = "powrprof.dll,SetSuspendState 0,1,0",
                UseShellExecute = true
            });
        }

        public void Shutdown()
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Shutdown");
            Process.Start(new ProcessStartInfo
            {
                FileName = "shutdown",
                Arguments = "/s /t 30",
                UseShellExecute = true
            });
        }

        public void Restart()
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Restart");
            Process.Start(new ProcessStartInfo
            {
                FileName = "shutdown",
                Arguments = "/r /t 30",
                UseShellExecute = true
            });
        }

        // ===== SCREENSHOT =====
        public string TakeScreenshot()
        {
            try
            {
                var bounds = System.Windows.Forms.Screen.PrimaryScreen.Bounds;
                using var bitmap = new Bitmap(bounds.Width, bounds.Height);
                using var g = Graphics.FromImage(bitmap);
                g.CopyFromScreen(Point.Empty, Point.Empty, bounds.Size);
                
                var path = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.MyPictures),
                    $"Screenshot_{DateTime.Now:yyyyMMdd_HHmmss}.png"
                );
                bitmap.Save(path, ImageFormat.Png);
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Screenshot saved: {path}");
                return path;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Screenshot error: {ex.Message}");
                return null;
            }
        }

        // ===== EXISTING METHODS =====
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
            System.Windows.Forms.SendKeys.SendWait(text);
        }

        public void OpenAndType(string exeName, string processName, string text)
        {
            OpenApplication(exeName);
            Thread.Sleep(2000);
            FocusWindow(processName);
            Thread.Sleep(500);
            TypeIntoApp(text);
        }
    }
}


