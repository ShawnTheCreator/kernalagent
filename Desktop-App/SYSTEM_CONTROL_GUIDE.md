# System Control Capabilities - Complete Guide

## 🎯 Overview

The Desktop App now has comprehensive system control capabilities, allowing it to manage your PC through voice commands or API calls. This includes power management, system information, volume control, display settings, process management, and much more.

## ✨ New Capabilities

### 1. **Power Management** 🔌

Full control over computer power states:

| Command | Voice Examples | Description |
|---------|---------------|-------------|
| **Shutdown** | "shutdown", "shut down computer", "turn off computer" | Shutdown the PC (with optional delay) |
| **Restart** | "restart", "reboot", "reset computer" | Restart the PC (with optional delay) |
| **Sleep** | "sleep", "put to sleep" | Put computer to sleep mode |
| **Hibernate** | "hibernate" | Hibernate the computer |
| **Lock** | "lock", "lock computer", "lock screen" | Lock the workstation |
| **Log Off** | "log off", "logoff", "sign out" | Log off current user |
| **Cancel Shutdown** | "cancel shutdown" | Cancel a pending shutdown/restart |

**Examples:**
```
"shutdown in 30 seconds"
"restart in 5 minutes"
"lock computer"
"put computer to sleep"
```

### 2. **Volume Control** 🔊

Control system audio:

| Command | Voice Examples | Description |
|---------|---------------|-------------|
| **Set Volume** | "volume 50", "set volume to 75" | Set volume to specific level (0-100) |
| **Mute/Unmute** | "mute", "unmute", "toggle mute" | Toggle system mute |
| **Volume Up** | "volume up", "increase volume" | Increase volume |
| **Volume Down** | "volume down", "decrease volume" | Decrease volume |

**Examples:**
```
"set volume to 50"
"mute"
"volume up"
```

### 3. **Display Control** 🖥️

Manage display settings:

| Command | Voice Examples | Description |
|---------|---------------|-------------|
| **Set Brightness** | "brightness 80", "set brightness to 50" | Set screen brightness (0-100) |
| **Turn Off Monitors** | "turn off screen", "turn off monitor" | Turn off all monitors |

**Examples:**
```
"set brightness to 75"
"turn off screen"
```

### 4. **System Information** 📊

Get detailed system information:

| Command | Voice Examples | Description |
|---------|---------------|-------------|
| **System Info** | "system info", "pc info", "computer info" | Get comprehensive system information |
| **Battery Status** | "battery", "battery status", "battery level" | Get battery information |
| **Network Status** | "network", "wifi", "internet" | Get network connection status |
| **Disk Space** | "disk space", "storage", "drive space" | Get disk space information |

**System Info Includes:**
- Computer name
- Username
- OS version
- CPU cores
- System uptime
- Memory usage (total/free)
- Battery status (if applicable)

**Examples:**
```
"system info"
"battery status"
"check disk space"
```

### 5. **Process Management** ⚙️

Manage running processes:

| Command | Voice Examples | Description |
|---------|---------------|-------------|
| **List Processes** | "running processes", "list processes" | Show top processes by memory usage |
| **Kill Process** | "kill chrome", "close notepad" | Terminate a specific process |
| **Launch App** | "open notepad", "launch calculator" | Start an application |

**Supported Applications:**
- notepad, calculator, paint
- word, excel, powerpoint
- chrome, edge, firefox
- explorer, cmd, powershell
- task manager, control panel, settings

**Examples:**
```
"list running processes"
"kill chrome"
"open calculator"
"launch task manager"
```

### 6. **Clipboard Operations** 📋

Manage clipboard content:

| Command | Voice Examples | Description |
|---------|---------------|-------------|
| **Get Clipboard** | "copy", "get clipboard", "what's in clipboard" | Read clipboard text |
| **Set Clipboard** | (API only) | Set clipboard text programmatically |

**Examples:**
```
"what's in clipboard"
```

### 7. **File System Operations** 📁

File system management:

| Command | Voice Examples | Description |
|---------|---------------|-------------|
| **Empty Recycle Bin** | "empty recycle bin", "empty trash" | Clear recycle bin |
| **Disk Info** | "disk space", "storage info" | Get disk space for all drives |

**Examples:**
```
"empty recycle bin"
"show disk space"
```

## 🔧 Technical Implementation

### Services Created

#### 1. **SystemControlService.cs**
Core service providing low-level system control:

```csharp
// Power Management
await SystemControlService.Instance.ShutdownAsync(delaySeconds);
await SystemControlService.Instance.RestartAsync(delaySeconds);
await SystemControlService.Instance.SleepAsync();
await SystemControlService.Instance.HibernateAsync();
await SystemControlService.Instance.LockAsync();
await SystemControlService.Instance.LogoffAsync();

// Volume Control
await SystemControlService.Instance.SetVolumeAsync(volume);
await SystemControlService.Instance.ToggleMuteAsync();

// Display Control
await SystemControlService.Instance.SetBrightnessAsync(brightness);
await SystemControlService.Instance.TurnOffMonitorsAsync();

// System Information
var info = await SystemControlService.Instance.GetSystemInfoAsync();
var battery = await SystemControlService.Instance.GetBatteryInfoAsync();
var network = await SystemControlService.Instance.GetNetworkInfoAsync();
var disks = await SystemControlService.Instance.GetDiskInfoAsync();

// Process Management
var processes = await SystemControlService.Instance.GetRunningProcessesAsync();
await SystemControlService.Instance.KillProcessAsync(processName);
await SystemControlService.Instance.LaunchAppAsync(appPath);

// Clipboard
var text = await SystemControlService.Instance.GetClipboardTextAsync();
await SystemControlService.Instance.SetClipboardTextAsync(text);

// File System
await SystemControlService.Instance.EmptyRecycleBinAsync();
```

#### 2. **SystemCommandHandler.cs**
Natural language command processor:

```csharp
// Process voice/text commands
var success = await SystemCommandHandler.Instance.ProcessCommandAsync("shutdown in 30 seconds");

// Subscribe to events
SystemCommandHandler.Instance.OnCommandExecuted += (message) => {
    // Command succeeded
};

SystemCommandHandler.Instance.OnCommandFailed += (error) => {
    // Command failed
};
```

### Windows APIs Used

The service uses various Windows APIs:
- **user32.dll**: ExitWindowsEx, LockWorkStation, ShowWindow
- **PowrProf.dll**: SetSuspendState (sleep/hibernate)
- **WMI**: System information, brightness control
- **Windows Runtime**: Battery, network, clipboard

## 📊 Data Models

### SystemInfo
```csharp
public class SystemInfo
{
    public string ComputerName { get; set; }
    public string UserName { get; set; }
    public string OSVersion { get; set; }
    public int ProcessorCount { get; set; }
    public bool Is64BitOS { get; set; }
    public TimeSpan Uptime { get; set; }
    public int? BatteryPercentage { get; set; }
    public bool IsCharging { get; set; }
    public long TotalMemoryMB { get; set; }
    public long FreeMemoryMB { get; set; }
}
```

### BatteryInfo
```csharp
public class BatteryInfo
{
    public int Percentage { get; set; }
    public bool IsCharging { get; set; }
    public string Status { get; set; }
}
```

### ProcessInfo
```csharp
public class ProcessInfo
{
    public int Id { get; set; }
    public string Name { get; set; }
    public string WindowTitle { get; set; }
    public long MemoryMB { get; set; }
    public DateTime StartTime { get; set; }
}
```

### NetworkInfo
```csharp
public class NetworkInfo
{
    public bool IsConnected { get; set; }
    public string ConnectionType { get; set; }
    public string SignalStrength { get; set; }
}
```

### DiskInfo
```csharp
public class DiskInfo
{
    public string Name { get; set; }
    public string Label { get; set; }
    public long TotalSizeGB { get; set; }
    public long FreeSizeGB { get; set; }
    public string DriveType { get; set; }
}
```

## 🎤 Voice Command Integration

### Integration with MainWindow

To integrate with voice commands, add to `MainWindow.xaml.cs`:

```csharp
private async Task ExecuteAgentCommand(string command)
{
    // Try system command first
    var handled = await SystemCommandHandler.Instance.ProcessCommandAsync(command);
    
    if (!handled)
    {
        // Fall back to other command handlers
        await ApiService.Instance.SendCommandAsync(command);
    }
}

// Subscribe to command events
SystemCommandHandler.Instance.OnCommandExecuted += (message) =>
{
    this.DispatcherQueue.TryEnqueue(() =>
    {
        AddToThoughtLog($"✅ {message}");
    });
};

SystemCommandHandler.Instance.OnCommandFailed += (error) =>
{
    this.DispatcherQueue.TryEnqueue(() =>
    {
        AddToThoughtLog($"❌ {error}");
    });
};
```

## 🔐 Security Considerations

### Permissions Required

Some operations require elevated permissions:
- **Shutdown/Restart**: Requires user privileges
- **Kill Process**: May require admin for system processes
- **Brightness Control**: Requires WMI access
- **Empty Recycle Bin**: Requires file system permissions

### Safety Features

1. **Confirmation for Critical Actions**: Shutdown/restart show warnings
2. **Delay Support**: Allow time to cancel shutdown/restart
3. **Error Handling**: All operations wrapped in try-catch
4. **Logging**: All actions logged to Debug output

## 📈 Usage Examples

### Example 1: Shutdown with Delay
```csharp
// Voice: "shutdown in 60 seconds"
await SystemControlService.Instance.ShutdownAsync(60);

// Cancel if needed
await SystemControlService.Instance.CancelShutdownAsync();
```

### Example 2: Get System Status
```csharp
var info = await SystemControlService.Instance.GetSystemInfoAsync();
var battery = await SystemControlService.Instance.GetBatteryInfoAsync();
var network = await SystemControlService.Instance.GetNetworkInfoAsync();

Console.WriteLine($"Computer: {info.ComputerName}");
Console.WriteLine($"Uptime: {info.Uptime}");
Console.WriteLine($"Battery: {battery.Percentage}%");
Console.WriteLine($"Network: {(network.IsConnected ? "Connected" : "Disconnected")}");
```

### Example 3: Process Management
```csharp
// Get top processes
var processes = await SystemControlService.Instance.GetRunningProcessesAsync();
foreach (var process in processes.Take(10))
{
    Console.WriteLine($"{process.Name}: {process.MemoryMB}MB");
}

// Kill a process
await SystemControlService.Instance.KillProcessAsync("chrome");

// Launch an app
await SystemControlService.Instance.LaunchAppAsync("notepad.exe");
```

## 🚀 Future Enhancements

Potential additions:
- [ ] **Screen Recording**: Capture screen/window
- [ ] **Screenshot**: Take screenshots programmatically
- [ ] **Webcam Control**: Access camera
- [ ] **Microphone Control**: Manage audio input
- [ ] **Window Management**: Minimize/maximize/arrange windows
- [ ] **Keyboard Shortcuts**: Send global hotkeys
- [ ] **Mouse Control**: Move cursor, click programmatically
- [ ] **Notification System**: Show Windows notifications
- [ ] **Scheduled Tasks**: Create/manage scheduled tasks
- [ ] **Service Management**: Start/stop Windows services
- [ ] **Registry Access**: Read/write registry (with caution)
- [ ] **Event Log**: Read Windows event logs

## 🧪 Testing

### Manual Testing Checklist

Power Management:
- [ ] Shutdown with delay
- [ ] Restart with delay
- [ ] Sleep mode
- [ ] Hibernate
- [ ] Lock screen
- [ ] Log off
- [ ] Cancel shutdown

Volume & Display:
- [ ] Set volume
- [ ] Mute/unmute
- [ ] Set brightness
- [ ] Turn off monitors

System Info:
- [ ] Get system info
- [ ] Get battery status
- [ ] Get network status
- [ ] Get disk space

Process Management:
- [ ] List processes
- [ ] Kill process
- [ ] Launch application

Other:
- [ ] Get clipboard
- [ ] Empty recycle bin

## 📝 Command Reference

### Complete Voice Command List

**Power:**
- "shutdown"
- "shutdown in 30 seconds"
- "restart"
- "sleep"
- "hibernate"
- "lock computer"
- "log off"

**Volume:**
- "set volume to 50"
- "mute"
- "volume up"

**Display:**
- "set brightness to 75"
- "turn off screen"

**System:**
- "system info"
- "battery status"
- "network status"
- "disk space"

**Processes:**
- "list processes"
- "kill chrome"
- "open notepad"

**Other:**
- "what's in clipboard"
- "empty recycle bin"

## ✅ Summary

The Desktop App now has **comprehensive PC control capabilities**:

✅ **Power Management** - Shutdown, restart, sleep, hibernate, lock, log off
✅ **Volume Control** - Set volume, mute/unmute
✅ **Display Control** - Brightness, turn off monitors
✅ **System Information** - Computer info, battery, network, disk space
✅ **Process Management** - List, kill, launch processes
✅ **Clipboard Operations** - Read/write clipboard
✅ **File System** - Empty recycle bin, disk info
✅ **Voice Command Support** - Natural language processing
✅ **Event-Driven** - Real-time feedback
✅ **Error Handling** - Graceful failure handling

Your Desktop App is now a **powerful system control center** that can manage your entire PC! 🎉
