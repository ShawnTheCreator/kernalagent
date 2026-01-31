using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using System.Drawing;
using System.Drawing.Imaging;
using System.Text;
using WindowsInput;

namespace Kernel_Agent.Services
{
    public class WindowsAutomation
    {
        private readonly bool _naturalExecution;
        private readonly Random _rng = new Random();

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
        
        // ===== Dialog Detection API Imports =====
        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
        
        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern IntPtr FindWindowEx(IntPtr hwndParent, IntPtr hwndChildAfter, string lpszClass, string lpszWindow);
        
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
        
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
        
        [DllImport("user32.dll")]
        private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
        
        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool GetCursorPos(out POINT lpPoint);
        
        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
        
        [DllImport("user32.dll")]
        private static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
        
        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [StructLayout(LayoutKind.Sequential)]
        private struct POINT
        {
            public int X;
            public int Y;
        }
        
        // Message constants for button clicks
        private const uint WM_COMMAND = 0x0111;
        private const uint BN_CLICKED = 0;
        
        // Button IDs for common dialogs
        private const int IDOK = 1;
        private const int IDCANCEL = 2;
        private const int IDYES = 6;
        private const int IDNO = 7;
        
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
            }},
            { "whatsapp.exe", new[] {
                Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
                Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\WhatsApp\app-0.0.0\WhatsApp.exe"),
                Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\Programs\WhatsApp\WhatsApp.exe"),
                @"C:\Program Files\WhatsApp\WhatsApp.exe"
            }},
            { "telegram.exe", new[] {
                Environment.ExpandEnvironmentVariables(@"%APPDATA%\Telegram Desktop\Telegram.exe"),
                Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\Telegram Desktop\Telegram.exe")
            }},
            { "discord.exe", new[] {
                Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\Discord\Update.exe"),
                Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\Discord\app-1.0.0\Discord.exe")
            }},
            { "slack.exe", new[] {
                Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\slack\slack.exe"),
                @"C:\Program Files\Slack\slack.exe"
            }}
        };

        public WindowsAutomation()
        {
            _naturalExecution = IsNaturalExecutionEnabled();
        }

        private static bool IsNaturalExecutionEnabled()
        {
            var raw = Environment.GetEnvironmentVariable("NATURAL_EXECUTION");
            var style = Environment.GetEnvironmentVariable("EXECUTION_STYLE");
            if (!string.IsNullOrWhiteSpace(style) &&
                style.Trim().Equals("jarvis", StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }

            if (!string.IsNullOrWhiteSpace(raw))
            {
                return raw.Trim().Equals("true", StringComparison.OrdinalIgnoreCase) || raw.Trim() == "1";
            }

            return false;
        }

        // ===== OPEN APPLICATION =====
        public bool OpenApplication(string exeName)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opening: {exeName}");
                
                string processName = exeName.Replace(".exe", "").Replace(".EXE", "");

                try
                {
                    var existing = Process.GetProcessesByName(processName)
                        .FirstOrDefault(p => p.MainWindowHandle != IntPtr.Zero);
                    if (existing != null)
                    {
                        ShowWindow(existing.MainWindowHandle, SW_RESTORE);
                        SetForegroundWindow(existing.MainWindowHandle);
                        System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Focused existing app: {processName}");
                        return true;
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Focus existing app failed: {ex.Message}");
                }

                if (processName.Equals("whatsapp", StringComparison.OrdinalIgnoreCase))
                {
                    var customPath = Environment.GetEnvironmentVariable("WHATSAPP_EXE_PATH") ?? "";
                    if (!string.IsNullOrWhiteSpace(customPath) && File.Exists(customPath))
                    {
                        Process.Start(new ProcessStartInfo { FileName = customPath, UseShellExecute = true });
                        System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opened WhatsApp via WHATSAPP_EXE_PATH: {customPath}");
                        return WaitForAppReady(processName);
                    }

                    var aumid = Environment.GetEnvironmentVariable("WHATSAPP_AUMID") ?? "";
                    if (!string.IsNullOrWhiteSpace(aumid))
                    {
                        Process.Start(new ProcessStartInfo
                        {
                            FileName = "explorer.exe",
                            Arguments = $"shell:AppsFolder\\{aumid}",
                            UseShellExecute = true
                        });
                        System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opened WhatsApp via AUMID: {aumid}");
                        return WaitForAppReady(processName);
                    }
                }
                
                // Special handling for Chrome - open with default profile to skip profile picker
                if (exeName.ToLowerInvariant().Contains("chrome"))
                {
                    return OpenChromeWithProfile();
                }
                
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
                    return WaitForAppReady(processName);
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
                            return WaitForAppReady(processName);
                        }
                    }
                }

                // Method 3: Try start command
                try
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = "cmd.exe",
                        Arguments = $"/c start {processName}",
                        UseShellExecute = true,
                        CreateNoWindow = true
                    });
                    System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opened via start: {processName}");
                    return WaitForAppReady(processName);
                }
                catch { }

                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Could not open: {exeName}");
                return false;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Error opening {exeName}: {ex.Message}");
                return false;
            }
        }

        private bool WaitForAppReady(string processName)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Waiting for {processName} to be ready...");
                // Some apps like 'notepad' might have different process names (e.g. 'Notepad')
                // We'll try to find it leniently
                
                int maxRetries = 20; // Wait up to 10 seconds
                
                for (int i = 0; i < maxRetries; i++)
                {
                    var processes = Process.GetProcesses();
                    var target = processes.FirstOrDefault(p => 
                        p.ProcessName.Equals(processName, StringComparison.OrdinalIgnoreCase) ||
                        p.ProcessName.Contains(processName, StringComparison.OrdinalIgnoreCase));

                    if (target != null && target.MainWindowHandle != IntPtr.Zero)
                    {
                        target.WaitForInputIdle(500); // Wait for app to be idle
                        SetForegroundWindow(target.MainWindowHandle); // Force focus
                        Thread.Sleep(500); // Extra safety buffer
                        System.Diagnostics.Debug.WriteLine($"[AUTOMATION] {processName} is ready and focused.");
                        return true;
                    }
                    else if (target != null)
                    {
                        // Found process but no window yet
                        System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Found {processName}, waiting for window...");
                    }
                    
                    Thread.Sleep(500);
                }
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Timeout waiting for {processName}.");
                return false;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Error waiting for app: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Opens Chrome with default profile to skip the profile picker.
        /// Falls back to pressing Enter if profile picker appears.
        /// </summary>
        private bool OpenChromeWithProfile(string profileName = "Default")
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Opening Chrome with profile: {profileName}");
                
                // Find Chrome executable
                string chromePath = null;
                var paths = new[]
                {
                    @"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    @"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
                };
                
                foreach (var path in paths)
                {
                    if (File.Exists(path))
                    {
                        chromePath = path;
                        break;
                    }
                }
                
                if (chromePath == null)
                {
                    System.Diagnostics.Debug.WriteLine("[AUTOMATION] Chrome not found, trying shell execute");
                    Process.Start(new ProcessStartInfo { FileName = "chrome.exe", UseShellExecute = true });
                    return WaitForAppReadyAndSelectProfile("chrome");
                }
                
                // Open Chrome with profile directory to skip profile picker
                var startInfo = new ProcessStartInfo
                {
                    FileName = chromePath,
                    Arguments = $"--profile-directory=\"{profileName}\"",
                    UseShellExecute = true
                };
                
                Process.Start(startInfo);
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Chrome started with profile: {profileName}");
                
                return WaitForAppReady("chrome");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Chrome open error: {ex.Message}");
                // Fallback: try normal open and handle profile picker
                try
                {
                    Process.Start(new ProcessStartInfo { FileName = "chrome.exe", UseShellExecute = true });
                    return WaitForAppReadyAndSelectProfile("chrome");
                }
                catch
                {
                    return false;
                }
            }
        }
        
        /// <summary>
        /// Wait for app and if it's Chrome, press Enter to select first profile if picker appears.
        /// </summary>
        private bool WaitForAppReadyAndSelectProfile(string processName)
        {
            var result = WaitForAppReady(processName);
            
            if (result && processName.ToLowerInvariant().Contains("chrome"))
            {
                // Give a moment for profile picker to potentially appear
                Thread.Sleep(500);
                
                // Press Enter to select the default/first profile (works if profile picker is shown)
                System.Diagnostics.Debug.WriteLine("[AUTOMATION] Pressing Enter to select profile (if picker shown)");
                PressKey("enter");
                
                // Wait a bit more for actual Chrome window
                Thread.Sleep(1000);
            }
            
            return result;
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
            if (!_naturalExecution)
            {
                System.Windows.Forms.SendKeys.SendWait(text);
                return;
            }

            TypeIntoAppHumanized(text);
        }

        private void TypeIntoAppHumanized(string text)
        {
            if (string.IsNullOrEmpty(text))
            {
                return;
            }

            foreach (var ch in text)
            {
                if (ch == '\n' || ch == '\r')
                {
                    System.Windows.Forms.SendKeys.SendWait("{ENTER}");
                    Thread.Sleep(_rng.Next(80, 160));
                    continue;
                }

                if (ch == '\t')
                {
                    System.Windows.Forms.SendKeys.SendWait("{TAB}");
                    Thread.Sleep(_rng.Next(80, 160));
                    continue;
                }

                System.Windows.Forms.SendKeys.SendWait(EscapeSendKeysChar(ch));

                int delay = char.IsWhiteSpace(ch)
                    ? _rng.Next(60, 140)
                    : _rng.Next(30, 90);

                if (_rng.NextDouble() < 0.08)
                {
                    delay += _rng.Next(80, 180);
                }

                Thread.Sleep(delay);
            }
        }

        private static string EscapeSendKeysChar(char ch)
        {
            if (ch == '{') return "{{}";
            if (ch == '}') return "{}}";

            const string special = "+^%~()[]";
            if (special.Contains(ch))
            {
                return "{" + ch + "}";
            }

            return ch.ToString();
        }

        public void OpenAndType(string exeName, string processName, string text)
        {
            OpenApplication(exeName);
            Thread.Sleep(2000);
            FocusWindow(processName);
            Thread.Sleep(500);
            TypeIntoApp(text);
        }

        // ===== KEYBOARD SHORTCUTS =====
        
        // Virtual key codes for hotkeys
        private const byte VK_CONTROL = 0x11;
        private const byte VK_ALT = 0x12;
        private const byte VK_SHIFT = 0x10;
        private const byte VK_LWIN = 0x5B;
        private const byte VK_TAB = 0x09;
        private const byte VK_ENTER = 0x0D;
        private const byte VK_ESCAPE = 0x1B;
        private const byte VK_SPACE = 0x20;
        private const byte VK_BACKSPACE = 0x08;
        private const byte VK_DELETE = 0x2E;
        private const byte VK_LEFT = 0x25;
        private const byte VK_RIGHT = 0x27;
        private const byte VK_F5 = 0x74;
        
        // Media keys
        private const byte VK_MEDIA_PLAY_PAUSE = 0xB3;
        private const byte VK_MEDIA_NEXT_TRACK = 0xB0;
        private const byte VK_MEDIA_PREV_TRACK = 0xB1;
        private const byte VK_MEDIA_STOP = 0xB2;

        public void Copy()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Copy (Ctrl+C)");
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(0x43, 0, 0, UIntPtr.Zero); // C key
            keybd_event(0x43, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void Paste()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Paste (Ctrl+V)");
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(0x56, 0, 0, UIntPtr.Zero); // V key
            keybd_event(0x56, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void Cut()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Cut (Ctrl+X)");
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(0x58, 0, 0, UIntPtr.Zero); // X key
            keybd_event(0x58, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void Undo()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Undo (Ctrl+Z)");
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(0x5A, 0, 0, UIntPtr.Zero); // Z key
            keybd_event(0x5A, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void Redo()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Redo (Ctrl+Y)");
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(0x59, 0, 0, UIntPtr.Zero); // Y key
            keybd_event(0x59, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void SelectAll()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Select All (Ctrl+A)");
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(0x41, 0, 0, UIntPtr.Zero); // A key
            keybd_event(0x41, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void Save()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Save (Ctrl+S)");
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(0x53, 0, 0, UIntPtr.Zero); // S key
            keybd_event(0x53, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void AltTab()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Alt+Tab");
            keybd_event(VK_ALT, 0, 0, UIntPtr.Zero);
            keybd_event(VK_TAB, 0, 0, UIntPtr.Zero);
            keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_ALT, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void ShowDesktop()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Show Desktop (Win+D)");
            keybd_event(VK_LWIN, 0, 0, UIntPtr.Zero);
            keybd_event(0x44, 0, 0, UIntPtr.Zero); // D key
            keybd_event(0x44, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void PressKey(string key)
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Press key: {key}");
            byte vk = key.ToLower() switch
            {
                "enter" => VK_ENTER,
                "tab" => VK_TAB,
                "escape" or "esc" => VK_ESCAPE,
                "space" => VK_SPACE,
                "backspace" => VK_BACKSPACE,
                "delete" => VK_DELETE,
                _ => 0
            };
            if (vk != 0)
            {
                keybd_event(vk, 0, 0, UIntPtr.Zero);
                keybd_event(vk, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            }
        }

        public void Hotkey(string keys)
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Hotkey: {keys}");
            var parts = keys.ToLower().Split('+');
            var modifiers = new List<byte>();
            byte mainKey = 0;

            foreach (var part in parts)
            {
                switch (part.Trim())
                {
                    case "ctrl": modifiers.Add(VK_CONTROL); break;
                    case "alt": modifiers.Add(VK_ALT); break;
                    case "shift": modifiers.Add(VK_SHIFT); break;
                    case "win": modifiers.Add(VK_LWIN); break;
                    default:
                        if (part.Length == 1 && char.IsLetterOrDigit(part[0]))
                            mainKey = (byte)char.ToUpper(part[0]);
                        break;
                }
            }

            // Press modifiers
            foreach (var mod in modifiers)
                keybd_event(mod, 0, 0, UIntPtr.Zero);

            // Press main key
            if (mainKey != 0)
            {
                keybd_event(mainKey, 0, 0, UIntPtr.Zero);
                keybd_event(mainKey, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            }

            // Release modifiers
            foreach (var mod in modifiers)
                keybd_event(mod, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        // ===== MEDIA CONTROL =====
        public void MediaPlayPause()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Media Play/Pause");
            keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, UIntPtr.Zero);
            keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void MediaNext()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Media Next");
            keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, UIntPtr.Zero);
            keybd_event(VK_MEDIA_NEXT_TRACK, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void MediaPrevious()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Media Previous");
            keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, UIntPtr.Zero);
            keybd_event(VK_MEDIA_PREV_TRACK, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void MediaStop()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Media Stop");
            keybd_event(VK_MEDIA_STOP, 0, 0, UIntPtr.Zero);
            keybd_event(VK_MEDIA_STOP, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        // ===== BROWSER COMMANDS =====
        public void NewTab()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] New Tab (Ctrl+T)");
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(0x54, 0, 0, UIntPtr.Zero); // T key
            keybd_event(0x54, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void CloseTab()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Close Tab (Ctrl+W)");
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(0x57, 0, 0, UIntPtr.Zero); // W key
            keybd_event(0x57, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void Refresh()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Refresh (F5)");
            keybd_event(VK_F5, 0, 0, UIntPtr.Zero);
            keybd_event(VK_F5, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void GoBack()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Go Back (Alt+Left)");
            keybd_event(VK_ALT, 0, 0, UIntPtr.Zero);
            keybd_event(VK_LEFT, 0, 0, UIntPtr.Zero);
            keybd_event(VK_LEFT, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_ALT, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void GoForward()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Go Forward (Alt+Right)");
            keybd_event(VK_ALT, 0, 0, UIntPtr.Zero);
            keybd_event(VK_RIGHT, 0, 0, UIntPtr.Zero);
            keybd_event(VK_RIGHT, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_ALT, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        // ===== MOUSE CONTROL =====
        [DllImport("user32.dll")]
        private static extern bool SetCursorPos(int X, int Y);

        [DllImport("user32.dll")]
        private static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, UIntPtr dwExtraInfo);

        private const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
        private const uint MOUSEEVENTF_LEFTUP = 0x0004;
        private const uint MOUSEEVENTF_RIGHTDOWN = 0x0008;
        private const uint MOUSEEVENTF_RIGHTUP = 0x0010;
        private const uint MOUSEEVENTF_WHEEL = 0x0800;

        public void Click(int x, int y)
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Click at ({x}, {y})");
            MoveMouseInternal(x, y);
            mouse_event(MOUSEEVENTF_LEFTDOWN, x, y, 0, UIntPtr.Zero);
            mouse_event(MOUSEEVENTF_LEFTUP, x, y, 0, UIntPtr.Zero);
        }

        public void DoubleClick(int x, int y)
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Double click at ({x}, {y})");
            MoveMouseInternal(x, y);
            mouse_event(MOUSEEVENTF_LEFTDOWN, x, y, 0, UIntPtr.Zero);
            mouse_event(MOUSEEVENTF_LEFTUP, x, y, 0, UIntPtr.Zero);
            Thread.Sleep(_naturalExecution ? _rng.Next(60, 120) : 50);
            mouse_event(MOUSEEVENTF_LEFTDOWN, x, y, 0, UIntPtr.Zero);
            mouse_event(MOUSEEVENTF_LEFTUP, x, y, 0, UIntPtr.Zero);
        }

        public void RightClick(int x, int y)
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Right click at ({x}, {y})");
            MoveMouseInternal(x, y);
            mouse_event(MOUSEEVENTF_RIGHTDOWN, x, y, 0, UIntPtr.Zero);
            mouse_event(MOUSEEVENTF_RIGHTUP, x, y, 0, UIntPtr.Zero);
        }

        public void MoveMouse(int x, int y)
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Move mouse to ({x}, {y})");
            MoveMouseInternal(x, y);
        }

        private void MoveMouseInternal(int x, int y)
        {
            if (!_naturalExecution)
            {
                SetCursorPos(x, y);
                return;
            }

            if (!GetCursorPos(out var start))
            {
                SetCursorPos(x, y);
                return;
            }

            int steps = _rng.Next(12, 20);
            for (int i = 1; i <= steps; i++)
            {
                double t = i / (double)steps;
                double eased = t * t * (3 - 2 * t); // smoothstep
                int nx = start.X + (int)((x - start.X) * eased);
                int ny = start.Y + (int)((y - start.Y) * eased);
                SetCursorPos(nx, ny);
                Thread.Sleep(_rng.Next(5, 14));
            }

            Thread.Sleep(_rng.Next(20, 60));
        }

        public void Scroll(string direction, int amount = 3)
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Scroll {direction}");
            int wheelDelta = direction.ToLower() == "up" ? 120 * amount : -120 * amount;
            mouse_event(MOUSEEVENTF_WHEEL, 0, 0, (uint)wheelDelta, UIntPtr.Zero);
        }

        // ===== BRIGHTNESS (Windows 10/11) =====
        public void BrightnessUp(int amount = 10)
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Brightness up");
            // Use PowerShell to adjust brightness
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = "powershell",
                    Arguments = $"-Command \"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, [Math]::Min(100, (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness + {amount}))\"",
                    UseShellExecute = false,
                    CreateNoWindow = true
                });
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Brightness error: {ex.Message}");
            }
        }

        public void BrightnessDown(int amount = 10)
        {
            System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Brightness down");
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = "powershell",
                    Arguments = $"-Command \"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, [Math]::Max(0, (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness - {amount}))\"",
                    UseShellExecute = false,
                    CreateNoWindow = true
                });
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AUTOMATION] Brightness error: {ex.Message}");
            }
        }

        // ===== VIRTUAL DESKTOP CONTROL (Windows 10/11) =====
        public void SwitchDesktopLeft()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Switch Desktop Left (Win+Ctrl+Left)");
            keybd_event(VK_LWIN, 0, 0, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(VK_LEFT, 0, 0, UIntPtr.Zero);
            keybd_event(VK_LEFT, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void SwitchDesktopRight()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Switch Desktop Right (Win+Ctrl+Right)");
            keybd_event(VK_LWIN, 0, 0, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(VK_RIGHT, 0, 0, UIntPtr.Zero);
            keybd_event(VK_RIGHT, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void NewDesktop()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] New Desktop (Win+Ctrl+D)");
            keybd_event(VK_LWIN, 0, 0, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(0x44, 0, 0, UIntPtr.Zero); // D key
            keybd_event(0x44, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void CloseDesktop()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Close Desktop (Win+Ctrl+F4)");
            keybd_event(VK_LWIN, 0, 0, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(0x73, 0, 0, UIntPtr.Zero); // F4 key (0x73)
            keybd_event(0x73, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        public void TaskView()
        {
            System.Diagnostics.Debug.WriteLine("[AUTOMATION] Task View (Win+Tab)");
            keybd_event(VK_LWIN, 0, 0, UIntPtr.Zero);
            keybd_event(VK_TAB, 0, 0, UIntPtr.Zero);
            keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        // ===== DIALOG DETECTION AND HANDLING =====
        
        /// <summary>
        /// Information about a detected dialog window.
        /// </summary>
        public class DialogInfo
        {
            public IntPtr Handle { get; set; }
            public string Title { get; set; } = "";
            public string ClassName { get; set; } = "";
            public DialogType Type { get; set; } = DialogType.Unknown;
            public bool HasYesNo { get; set; }
            public bool HasOkCancel { get; set; }
        }
        
        public enum DialogType
        {
            Unknown,
            SaveAs,
            FileExists,
            Confirmation,
            Error,
            Warning
        }
        
        /// <summary>
        /// Check if a dialog window is currently visible (blocking interaction).
        /// </summary>
        public bool IsDialogPresent()
        {
            var dialogInfo = GetDialogInfo();
            return dialogInfo != null;
        }
        
        /// <summary>
        /// Get information about the currently visible dialog, if any.
        /// </summary>
        public DialogInfo? GetDialogInfo()
        {
            IntPtr foreground = GetForegroundWindow();
            if (foreground == IntPtr.Zero)
                return null;
            
            var className = new StringBuilder(256);
            GetClassName(foreground, className, 256);
            string classStr = className.ToString();
            
            var title = new StringBuilder(256);
            GetWindowText(foreground, title, 256);
            string titleStr = title.ToString();
            
            System.Diagnostics.Debug.WriteLine($"[DIALOG] Foreground: class='{classStr}' title='{titleStr}'");
            
            // Check for common dialog classes
            bool isDialog = classStr.Contains("#32770") ||  // Standard Windows dialog
                           classStr.Contains("Dialog") ||
                           classStr.Contains("Popup") ||
                           titleStr.Contains("Save As") ||
                           titleStr.Contains("Confirm") ||
                           titleStr.Contains("Replace") ||
                           titleStr.Contains("already exists");
            
            if (!isDialog)
                return null;
            
            var info = new DialogInfo
            {
                Handle = foreground,
                Title = titleStr,
                ClassName = classStr,
                Type = DetectDialogType(titleStr, classStr)
            };
            
            // Check for Yes/No buttons
            IntPtr yesBtn = FindWindowEx(foreground, IntPtr.Zero, "Button", "Yes");
            IntPtr noBtn = FindWindowEx(foreground, IntPtr.Zero, "Button", "No");
            info.HasYesNo = yesBtn != IntPtr.Zero && noBtn != IntPtr.Zero;
            
            // Alt: check for &Yes (accelerator key)
            if (!info.HasYesNo)
            {
                yesBtn = FindWindowEx(foreground, IntPtr.Zero, "Button", "&Yes");
                noBtn = FindWindowEx(foreground, IntPtr.Zero, "Button", "&No");
                info.HasYesNo = yesBtn != IntPtr.Zero && noBtn != IntPtr.Zero;
            }
            
            // Check for OK/Cancel buttons
            IntPtr okBtn = FindWindowEx(foreground, IntPtr.Zero, "Button", "OK");
            IntPtr cancelBtn = FindWindowEx(foreground, IntPtr.Zero, "Button", "Cancel");
            info.HasOkCancel = okBtn != IntPtr.Zero && cancelBtn != IntPtr.Zero;
            
            System.Diagnostics.Debug.WriteLine($"[DIALOG] Detected: type={info.Type} hasYesNo={info.HasYesNo} hasOkCancel={info.HasOkCancel}");
            
            return info;
        }
        
        /// <summary>
        /// Detect the type of dialog based on title and class.
        /// </summary>
        private DialogType DetectDialogType(string title, string className)
        {
            string lowerTitle = title.ToLower();
            
            if (lowerTitle.Contains("save as"))
                return DialogType.SaveAs;
            
            if (lowerTitle.Contains("already exists") || 
                lowerTitle.Contains("replace") ||
                lowerTitle.Contains("overwrite"))
                return DialogType.FileExists;
            
            if (lowerTitle.Contains("confirm") ||
                lowerTitle.Contains("are you sure"))
                return DialogType.Confirmation;
            
            if (lowerTitle.Contains("error"))
                return DialogType.Error;
            
            if (lowerTitle.Contains("warning"))
                return DialogType.Warning;
            
            // Check class name for standard dialog
            if (className.Contains("#32770"))
                return DialogType.Confirmation;
            
            return DialogType.Unknown;
        }
        
        /// <summary>
        /// Click the Yes button on a dialog.
        /// Returns true if successful.
        /// </summary>
        public bool DismissDialogWithYes()
        {
            IntPtr foreground = GetForegroundWindow();
            if (foreground == IntPtr.Zero)
                return false;
            
            // Try different button texts
            string[] yesTexts = { "Yes", "&Yes", "Да" };
            foreach (var text in yesTexts)
            {
                IntPtr btn = FindWindowEx(foreground, IntPtr.Zero, "Button", text);
                if (btn != IntPtr.Zero)
                {
                    System.Diagnostics.Debug.WriteLine($"[DIALOG] Clicking Yes button");
                    PostMessage(btn, WM_COMMAND, (IntPtr)(BN_CLICKED << 16 | IDYES), btn);
                    Thread.Sleep(100);
                    return true;
                }
            }
            
            // Alternative: press Enter (often activates default button)
            System.Diagnostics.Debug.WriteLine($"[DIALOG] No Yes button found, pressing Enter");
            keybd_event(VK_ENTER, 0, 0, UIntPtr.Zero);
            keybd_event(VK_ENTER, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            Thread.Sleep(100);
            return true;
        }
        
        /// <summary>
        /// Click the No/Cancel button on a dialog.
        /// </summary>
        public bool DismissDialogWithNo()
        {
            IntPtr foreground = GetForegroundWindow();
            if (foreground == IntPtr.Zero)
                return false;
            
            string[] noTexts = { "No", "&No", "Cancel", "Нет" };
            foreach (var text in noTexts)
            {
                IntPtr btn = FindWindowEx(foreground, IntPtr.Zero, "Button", text);
                if (btn != IntPtr.Zero)
                {
                    System.Diagnostics.Debug.WriteLine($"[DIALOG] Clicking No/Cancel button");
                    PostMessage(btn, WM_COMMAND, (IntPtr)(BN_CLICKED << 16 | IDNO), btn);
                    Thread.Sleep(100);
                    return true;
                }
            }
            
            // Alternative: press Escape
            System.Diagnostics.Debug.WriteLine($"[DIALOG] No button found, pressing Escape");
            keybd_event(VK_ESCAPE, 0, 0, UIntPtr.Zero);
            keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            Thread.Sleep(100);
            return true;
        }
        
        /// <summary>
        /// Wait for a dialog to appear after an action.
        /// Returns dialog info if one appears within timeout, null otherwise.
        /// </summary>
        public async Task<DialogInfo?> WaitForDialogAsync(int timeoutMs = 1000)
        {
            var sw = Stopwatch.StartNew();
            while (sw.ElapsedMilliseconds < timeoutMs)
            {
                var dialog = GetDialogInfo();
                if (dialog != null)
                {
                    System.Diagnostics.Debug.WriteLine($"[DIALOG] Dialog appeared: {dialog.Title}");
                    return dialog;
                }
                await Task.Delay(100);
            }
            return null;
        }
    }
}


