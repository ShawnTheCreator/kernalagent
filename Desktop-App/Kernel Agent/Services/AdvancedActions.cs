using System;
using System.Collections.Generic;
using System.IO;
using System.Diagnostics;
using System.Linq;
using System.Threading;
using System.Text;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Advanced automation actions: File ops, process control, system interaction
    /// Drop-in extension for SmartExecutor - just copy the action cases from here
    /// </summary>
    public static class AdvancedActions
    {
        // ===== FILE OPERATIONS =====
        public static bool CreateFile(string filePath, string content)
        {
            try
            {
                var directory = Path.GetDirectoryName(filePath);
                if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
                    Directory.CreateDirectory(directory);
                File.WriteAllText(filePath, content);
                Debug.WriteLine($"[ADVANCED] ✓ Created file: {filePath}");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ADVANCED] ✗ Create file failed: {ex.Message}");
                return false;
            }
        }

        public static bool DeleteFile(string filePath)
        {
            try
            {
                if (File.Exists(filePath))
                {
                    File.Delete(filePath);
                    Debug.WriteLine($"[ADVANCED] ✓ Deleted file: {filePath}");
                    return true;
                }
                else if (Directory.Exists(filePath))
                {
                    Directory.Delete(filePath, true);
                    Debug.WriteLine($"[ADVANCED] ✓ Deleted directory: {filePath}");
                    return true;
                }
                return false;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ADVANCED] ✗ Delete failed: {ex.Message}");
                return false;
            }
        }

        public static bool CopyFile(string source, string destination)
        {
            try
            {
                var destDir = Path.GetDirectoryName(destination);
                if (!string.IsNullOrEmpty(destDir) && !Directory.Exists(destDir))
                    Directory.CreateDirectory(destDir);
                File.Copy(source, destination, true);
                Debug.WriteLine($"[ADVANCED] ✓ Copied {source} to {destination}");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ADVANCED] ✗ Copy failed: {ex.Message}");
                return false;
            }
        }

        public static bool MoveFile(string source, string destination)
        {
            try
            {
                var destDir = Path.GetDirectoryName(destination);
                if (!string.IsNullOrEmpty(destDir) && !Directory.Exists(destDir))
                    Directory.CreateDirectory(destDir);
                if (File.Exists(destination))
                    File.Delete(destination);
                File.Move(source, destination);
                Debug.WriteLine($"[ADVANCED] ✓ Moved {source} to {destination}");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ADVANCED] ✗ Move failed: {ex.Message}");
                return false;
            }
        }

        public static string ListFiles(string dirPath)
        {
            try
            {
                if (!Directory.Exists(dirPath))
                    return "";
                var files = Directory.GetFiles(dirPath);
                var folders = Directory.GetDirectories(dirPath);
                var all = files.Concat(folders).ToList();
                return string.Join("|", all.Select(p => Path.GetFileName(p)));
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ADVANCED] ✗ List files failed: {ex.Message}");
                return "";
            }
        }

        public static string FindFiles(string dirPath, string pattern)
        {
            try
            {
                if (!Directory.Exists(dirPath))
                    return "";
                var files = Directory.GetFiles(dirPath, pattern);
                return string.Join("|", files.Select(f => Path.GetFileName(f)));
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ADVANCED] ✗ Find files failed: {ex.Message}");
                return "";
            }
        }

        public static bool RenameFile(string filePath, string newName)
        {
            try
            {
                var directory = Path.GetDirectoryName(filePath);
                var newPath = Path.Combine(directory, newName);
                if (File.Exists(filePath))
                {
                    File.Move(filePath, newPath, true);
                    return true;
                }
                return false;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ADVANCED] ✗ Rename failed: {ex.Message}");
                return false;
            }
        }

        // ===== PROCESS CONTROL =====
        public static List<string> GetProcessList()
        {
            try
            {
                return Process.GetProcesses()
                    .Select(p => p.ProcessName)
                    .Distinct()
                    .OrderBy(p => p)
                    .ToList();
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ADVANCED] ✗ Get process list failed: {ex.Message}");
                return new List<string>();
            }
        }

        public static bool KillProcess(string processName)
        {
            try
            {
                var cleanName = processName.Replace(".exe", "").Replace(".EXE", "");
                var processes = Process.GetProcessesByName(cleanName);
                foreach (var proc in processes)
                {
                    proc.Kill();
                    proc.WaitForExit(3000);
                }
                return processes.Length > 0;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ADVANCED] ✗ Kill process failed: {ex.Message}");
                return false;
            }
        }

        public static bool IsProcessRunning(string processName)
        {
            try
            {
                var cleanName = processName.Replace(".exe", "");
                var processes = Process.GetProcessesByName(cleanName);
                return processes.Length > 0;
            }
            catch
            {
                return false;
            }
        }

        // ===== CLIPBOARD =====
        public static bool CopyToClipboard(string content)
        {
            try
            {
                var thread = new Thread(() =>
                {
                    System.Windows.Forms.Clipboard.SetText(content);
                });
                thread.SetApartmentState(ApartmentState.STA);
                thread.Start();
                thread.Join(1000);
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ADVANCED] ✗ Clipboard copy failed: {ex.Message}");
                return false;
            }
        }

        public static string PasteFromClipboard()
        {
            try
            {
                string clipboard = "";
                var thread = new Thread(() =>
                {
                    try
                    {
                        clipboard = System.Windows.Forms.Clipboard.GetText();
                    }
                    catch { }
                });
                thread.SetApartmentState(ApartmentState.STA);
                thread.Start();
                thread.Join(1000);
                return clipboard;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ADVANCED] ✗ Clipboard paste failed: {ex.Message}");
                return "";
            }
        }
    }
}
