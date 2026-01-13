using System;
using System.Diagnostics;
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

        public void OpenApplication(string exeName)
        {
            Process.Start(exeName);
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
