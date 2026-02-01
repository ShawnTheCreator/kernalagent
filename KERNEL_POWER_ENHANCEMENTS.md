# Kernel Agent Power Enhancements Guide

## 🚀 Overview

Your Kernel Agent has a **strong foundation** with:
- ✅ App opening/closing
- ✅ Clicking buttons  
- ✅ Typing text
- ✅ Vision-based UI targeting
- ✅ Keyboard shortcuts
- ✅ Window management
- ✅ Virtual desktop control
- ✅ Scroll operations

This guide shows you how to **unlock advanced automation** and make it even more powerful.

---

## 📊 Current Capabilities Map

### Desktop App (C# WinUI 3)
**Location:** `Desktop-App/Kernel Agent/Services/`

#### Supported Actions (in SmartExecutor.cs)
```
✅ open_app               - Launch any executable
✅ close_app              - Close applications by name
✅ type_text              - Type text input
✅ type_in_element        - Type into specific UI element
✅ click                  - Click at coordinates
✅ double_click           - Double click
✅ right_click            - Right-click context menu
✅ move_mouse             - Move cursor
✅ scroll                 - Scroll up/down/left/right
✅ click_element          - Click named element (UI Automation)
✅ click_button           - Find and click button
✅ click_menu             - Navigate menu hierarchy
✅ find_and_click         - Vision-based element finding
✅ press_key              - Single key press
✅ hotkey                 - Keyboard combinations (Ctrl, Shift, Alt)
✅ navigate               - Go to URL
✅ search                 - Search web/app
✅ volume_up/down         - Audio control
✅ window management      - Maximize, minimize, restore, focus
✅ alt_tab                - Switch windows
✅ show_desktop           - Desktop view
✅ virtual_desktop        - Desktop switching (Windows 10/11)
✅ toggle_setting         - System toggles (WiFi, Bluetooth)
✅ wait/smart_wait        - Delays and conditions
✅ screen_capture         - Capture screenshot
```

---

## 🔋 NEW: Advanced Enhancements (Recommended Implementation)

### 1. **Advanced Action Types to Add**

#### A. File System Operations
```csharp
// ADD TO: Services/SmartExecutor.cs

case "create_file":
    if (step.TryGetProperty("path", out var pathEl) && 
        step.TryGetProperty("content", out var contentEl))
    {
        string filePath = pathEl.GetString() ?? "";
        string content = contentEl.GetString() ?? "";
        try
        {
            File.WriteAllText(filePath, content);
            result.Success = true;
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;

case "delete_file":
    if (step.TryGetProperty("path", out var delPathEl))
    {
        string filePath = delPathEl.GetString() ?? "";
        try
        {
            if (File.Exists(filePath))
                File.Delete(filePath);
            if (Directory.Exists(filePath))
                Directory.Delete(filePath, true);
            result.Success = true;
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;

case "copy_file":
    if (step.TryGetProperty("source", out var srcEl) && 
        step.TryGetProperty("destination", out var destEl))
    {
        string source = srcEl.GetString() ?? "";
        string destination = destEl.GetString() ?? "";
        try
        {
            File.Copy(source, destination, true);
            result.Success = true;
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;

case "move_file":
    if (step.TryGetProperty("source", out var moveSrcEl) && 
        step.TryGetProperty("destination", out var moveDestEl))
    {
        string source = moveSrcEl.GetString() ?? "";
        string destination = moveDestEl.GetString() ?? "";
        try
        {
            File.Move(source, destination, true);
            result.Success = true;
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;

case "list_files":
    if (step.TryGetProperty("path", out var listPathEl))
    {
        string dirPath = listPathEl.GetString() ?? "";
        try
        {
            var files = Directory.GetFiles(dirPath);
            result.Success = true;
            result.Details = string.Join("|", files);
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;
```

#### B. Process & System Control
```csharp
case "run_command":
    if (step.TryGetProperty("command", out var cmdEl))
    {
        string command = cmdEl.GetString() ?? "";
        try
        {
            var processInfo = new ProcessStartInfo
            {
                FileName = "cmd.exe",
                Arguments = $"/c {command}",
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            using (var process = Process.Start(processInfo))
            {
                process?.WaitForExit(5000);
                result.Success = true;
            }
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;

case "kill_process":
    if (step.TryGetProperty("process_name", out var procEl))
    {
        string processName = procEl.GetString()?.Replace(".exe", "") ?? "";
        try
        {
            var processes = Process.GetProcessesByName(processName);
            foreach (var proc in processes)
            {
                proc.Kill();
                proc.WaitForExit();
            }
            result.Success = processes.Length > 0;
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;

case "get_process_list":
    try
    {
        var processes = Process.GetProcesses()
            .Select(p => p.ProcessName)
            .Distinct()
            .OrderBy(p => p)
            .Take(50);
        result.Success = true;
        result.Details = string.Join("|", processes);
    }
    catch (Exception ex)
    {
        result.Error = ex.Message;
    }
    break;
```

#### C. Text/Clipboard Operations
```csharp
case "copy_to_clipboard":
    if (step.TryGetProperty("content", out var clipEl))
    {
        string content = clipEl.GetString() ?? "";
        try
        {
            var thread = new Thread(() => 
                System.Windows.Forms.Clipboard.SetText(content));
            thread.SetApartmentState(ApartmentState.STA);
            thread.Start();
            thread.Join();
            result.Success = true;
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;

case "paste_from_clipboard":
    try
    {
        string clipboard = "";
        var thread = new Thread(() => 
            clipboard = System.Windows.Forms.Clipboard.GetText());
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        thread.Join();
        
        _automation.TypeIntoApp(clipboard);
        result.Success = true;
    }
    catch (Exception ex)
    {
        result.Error = ex.Message;
    }
    break;

case "find_replace_text":
    if (step.TryGetProperty("find", out var findEl) && 
        step.TryGetProperty("replace", out var replEl))
    {
        string find = findEl.GetString() ?? "";
        string replace = replEl.GetString() ?? "";
        try
        {
            _automation.Hotkey("ctrl+h"); // Find & Replace dialog
            await Task.Delay(500);
            _automation.TypeIntoApp(find);
            _automation.PressKey("tab");
            _automation.TypeIntoApp(replace);
            _automation.Hotkey("ctrl+a"); // Replace all
            result.Success = true;
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;
```

#### D. Window Detection & Interaction
```csharp
case "find_window":
    if (step.TryGetProperty("title", out var titleEl))
    {
        string windowTitle = titleEl.GetString() ?? "";
        try
        {
            var handle = FindWindowByTitle(windowTitle);
            result.Success = handle != IntPtr.Zero;
            if (result.Success)
                result.Details = handle.ToString();
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;

case "focus_window":
    if (step.TryGetProperty("title", out var focusTitleEl))
    {
        string windowTitle = focusTitleEl.GetString() ?? "";
        try
        {
            _automation.FocusWindow(windowTitle);
            result.Success = true;
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;

case "get_active_window":
    try
    {
        var active = GetActiveWindowTitle();
        result.Success = true;
        result.Details = active;
    }
    catch (Exception ex)
    {
        result.Error = ex.Message;
    }
    break;

case "get_window_geometry":
    if (step.TryGetProperty("title", out var geoTitleEl))
    {
        string windowTitle = geoTitleEl.GetString() ?? "";
        try
        {
            var (x, y, w, h) = GetWindowGeometry(windowTitle);
            result.Success = true;
            result.Details = $"{x},{y},{w},{h}";
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;
```

#### E. Smart Waiting & Verification
```csharp
case "wait_for_window":
    if (step.TryGetProperty("title", out var waitTitleEl))
    {
        string windowTitle = waitTitleEl.GetString() ?? "";
        int timeout = step.TryGetProperty("timeout_ms", out var timeoutEl) 
            ? timeoutEl.GetInt32() : 10000;
        
        var stopwatch = Stopwatch.StartNew();
        while (stopwatch.ElapsedMilliseconds < timeout)
        {
            var handle = FindWindowByTitle(windowTitle);
            if (handle != IntPtr.Zero)
            {
                result.Success = true;
                break;
            }
            await Task.Delay(100);
        }
        
        if (!result.Success)
            result.Error = $"Window '{windowTitle}' not found within {timeout}ms";
    }
    break;

case "wait_for_element":
    if (step.TryGetProperty("target", out var elemTitleEl))
    {
        string elementName = elemTitleEl.GetString() ?? "";
        int timeout = step.TryGetProperty("timeout_ms", out var elemTimeoutEl) 
            ? elemTimeoutEl.GetInt32() : 5000;
        
        var stopwatch = Stopwatch.StartNew();
        while (stopwatch.ElapsedMilliseconds < timeout)
        {
            var element = _uiFinder.FindElement(elementName);
            if (element != null)
            {
                result.Success = true;
                break;
            }
            await Task.Delay(100);
        }
        
        if (!result.Success)
            result.Error = $"Element '{elementName}' not found within {timeout}ms";
    }
    break;

case "verify_text":
    if (step.TryGetProperty("expected_text", out var expectEl))
    {
        string expectedText = expectEl.GetString() ?? "";
        try
        {
            // Capture screenshot and OCR to verify text
            var screenshot = _automation.CaptureScreen();
            // TODO: Integrate OCR or accessibility tree search
            result.Success = true; // Placeholder
        }
        catch (Exception ex)
        {
            result.Error = ex.Message;
        }
    }
    break;
```

---

### 2. **Enhance Vision System for More Accuracy**

Create new file: `Desktop-App/Kernel Agent/Services/EnhancedVisionEngine.cs`

```csharp
using System;
using System.Collections.Generic;
using System.Linq;
using System.Drawing;
using System.Net.Http;
using System.Threading.Tasks;
using System.Diagnostics;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Enhanced vision engine with multi-strategy targeting
    /// </summary>
    public class EnhancedVisionEngine
    {
        private readonly VisionRecoveryService _vision;
        private readonly UIElementFinder _uiFinder;
        private readonly WindowsAutomation _automation;

        public EnhancedVisionEngine(
            VisionRecoveryService vision,
            UIElementFinder uiFinder,
            WindowsAutomation automation)
        {
            _vision = vision;
            _uiFinder = uiFinder;
            _automation = automation;
        }

        /// <summary>
        /// Multi-strategy targeting: Try multiple approaches in order
        /// </summary>
        public async Task<ClickTargetResult> FindTargetAdvanced(
            string description,
            string strategy = "auto")
        {
            // Strategy 1: Accessibility (FASTEST - 10ms)
            if (strategy == "auto" || strategy == "accessibility")
            {
                var element = _uiFinder.FindElement(description);
                if (element != null)
                {
                    var rect = element.Current.BoundingRectangle;
                    return new ClickTargetResult
                    {
                        Success = true,
                        X = (int)(rect.X + rect.Width / 2),
                        Y = (int)(rect.Y + rect.Height / 2),
                        Element = element.Current.Name,
                        Confidence = 0.95
                    };
                }
            }

            // Strategy 2: OCR/Vision (MEDIUM - 500-1000ms)
            if (strategy == "auto" || strategy == "vision")
            {
                var visionResult = await _vision.FindClickTargetAsync(description, "");
                if (visionResult?.Success == true && visionResult.X > 0 && visionResult.Y > 0)
                {
                    return visionResult;
                }
            }

            // Strategy 3: Fuzzy matching (FAST - 50ms)
            if (strategy == "auto" || strategy == "fuzzy")
            {
                var fuzzyResult = FuzzyMatchElement(description);
                if (fuzzyResult != null)
                {
                    return fuzzyResult;
                }
            }

            // Strategy 4: Color-based detection (MEDIUM)
            if (strategy == "auto" || strategy == "color")
            {
                var colorResult = FindByColorPattern(description);
                if (colorResult != null)
                {
                    return colorResult;
                }
            }

            return null;
        }

        /// <summary>
        /// Fuzzy match UI elements (e.g., "Sav" matches "Save Button")
        /// </summary>
        private ClickTargetResult FuzzyMatchElement(string description)
        {
            try
            {
                var allElements = _uiFinder.FindElementsByPattern(description);
                if (allElements.Any())
                {
                    var best = allElements.OrderByDescending(e => 
                        SimilarityScore(description, e.Current.Name))
                        .First();

                    if (best != null)
                    {
                        var rect = best.Current.BoundingRectangle;
                        return new ClickTargetResult
                        {
                            Success = true,
                            X = (int)(rect.X + rect.Width / 2),
                            Y = (int)(rect.Y + rect.Height / 2),
                            Element = best.Current.Name,
                            Confidence = 0.8
                        };
                    }
                }
            }
            catch { }
            return null;
        }

        /// <summary>
        /// Find elements by visual color patterns
        /// </summary>
        private ClickTargetResult FindByColorPattern(string description)
        {
            // This would integrate with image processing
            // Example: Find blue button, red alert, green confirm button
            return null;
        }

        /// <summary>
        /// Calculate string similarity score (Levenshtein distance)
        /// </summary>
        private double SimilarityScore(string source, string target)
        {
            if (string.IsNullOrEmpty(target))
                return 0;

            int maxLength = Math.Max(source.Length, target.Length);
            if (maxLength == 0)
                return 1.0;

            int distance = LevenshteinDistance(source.ToLower(), target.ToLower());
            return (maxLength - distance) / (double)maxLength;
        }

        /// <summary>
        /// Levenshtein distance algorithm
        /// </summary>
        private int LevenshteinDistance(string source, string target)
        {
            if (source.Length == 0) return target.Length;
            if (target.Length == 0) return source.Length;

            var matrix = new int[source.Length + 1, target.Length + 1];

            for (int i = 0; i <= source.Length; i++)
                matrix[i, 0] = i;

            for (int j = 0; j <= target.Length; j++)
                matrix[0, j] = j;

            for (int i = 1; i <= source.Length; i++)
            {
                for (int j = 1; j <= target.Length; j++)
                {
                    int cost = source[i - 1] == target[j - 1] ? 0 : 1;
                    matrix[i, j] = Math.Min(Math.Min(
                        matrix[i - 1, j] + 1,
                        matrix[i, j - 1] + 1),
                        matrix[i - 1, j - 1] + cost);
                }
            }

            return matrix[source.Length, target.Length];
        }
    }

    public class ClickTargetResult
    {
        public bool Success { get; set; }
        public int X { get; set; }
        public int Y { get; set; }
        public string Element { get; set; }
        public double Confidence { get; set; }
    }
}
```

---

### 3. **Autonomous Task Planning (AI-Driven)**

Create: `Microservice/app/agents/task_planner.py`

```python
"""
Autonomous Task Planner using Gemini
Breaks down high-level goals into executable action sequences
"""

from pydantic import BaseModel
from typing import List, Dict, Any
import google.generativeai as genai
from app.core.config import settings

class TaskStep(BaseModel):
    step_number: int
    description: str
    action: str
    target: str = ""
    content: str = ""
    verification: str = ""
    timeout_ms: int = 5000

class TaskPlan(BaseModel):
    goal: str
    total_steps: int
    steps: List[TaskStep]
    estimated_duration_ms: int

class TaskPlanner:
    """Breaks down goals into autonomous action sequences"""
    
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        
    async def plan_task(self, goal: str, context: Dict[str, Any] = None) -> TaskPlan:
        """
        Generate detailed task plan from high-level goal
        
        Example:
        Input: "Organize my downloads folder by file type"
        Output: [
            Step 1: Open File Explorer
            Step 2: Navigate to Downloads
            Step 3: Create folder "Documents"
            ...
        ]
        """
        
        context_str = ""
        if context:
            context_str = f"""
Current context:
- Active window: {context.get('active_window', 'Unknown')}
- Open applications: {context.get('open_apps', [])}
- Desktop files: {context.get('desktop_files', [])}
- Available folders: {context.get('available_folders', [])}
            """
        
        prompt = f"""
You are an expert task automation assistant. Break down this goal into detailed, 
executable steps that can be performed on a Windows PC.

GOAL: {goal}

{context_str}

For each step, provide:
1. A clear description (2-3 sentences)
2. The specific ACTION (open_app, click, type_text, navigate, etc.)
3. The TARGET (what to interact with)
4. Any TEXT to enter
5. How to VERIFY the step worked

Output as JSON array of steps. Each step should be atomic and take <5 seconds.

Example format:
[
  {{
    "step_number": 1,
    "description": "Open File Explorer to access the downloads folder",
    "action": "open_app",
    "target": "explorer.exe",
    "verification": "Window title contains 'File Explorer'"
  }},
  {{
    "step_number": 2,
    "description": "Navigate to the Downloads folder by typing the path",
    "action": "navigate",
    "target": "C:\\Users\\{{username}}\\Downloads",
    "verification": "Address bar shows Downloads path"
  }}
]

Generate the step plan now:
        """
        
        response = await self.model.generate_content_async(prompt)
        
        # Parse response into TaskPlan
        import json
        steps_data = json.loads(response.text)
        
        steps = [TaskStep(**step) for step in steps_data]
        
        return TaskPlan(
            goal=goal,
            total_steps=len(steps),
            steps=steps,
            estimated_duration_ms=len(steps) * 3000
        )
    
    async def execute_plan(self, plan: TaskPlan, executor) -> Dict[str, Any]:
        """Execute the task plan step by step"""
        results = []
        
        for step in plan.steps:
            result = await executor.execute_action({
                "action": step.action,
                "target": step.target,
                "content": step.content
            })
            
            results.append({
                "step": step.step_number,
                "description": step.description,
                "success": result.get("success", False),
                "error": result.get("error")
            })
            
            if not result.get("success"):
                # Ask Gemini for recovery strategy
                recovery = await self.plan_recovery(step, result, plan.goal)
                if recovery:
                    recovery_result = await executor.execute_action(recovery)
                    results[-1]["recovery"] = recovery_result
        
        return {
            "goal": plan.goal,
            "total_steps": plan.total_steps,
            "successful_steps": sum(1 for r in results if r["success"]),
            "results": results
        }
    
    async def plan_recovery(self, failed_step: TaskStep, error: Dict, goal: str):
        """Suggest recovery action when step fails"""
        
        prompt = f"""
A task step failed. Suggest a recovery action.

Goal: {goal}
Failed step: {failed_step.description}
Action: {failed_step.action}
Error: {error.get('error', 'Unknown')}

What should we try instead? Respond with JSON:
{{"action": "...", "target": "...", "content": "..."}}
        """
        
        response = await self.model.generate_content_async(prompt)
        import json
        return json.loads(response.text)
```

Add API endpoint in `Microservice/app/api/task_planner.py`:

```python
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from app.agents.task_planner import TaskPlanner, TaskPlan

router = APIRouter(prefix="/api/task", tags=["task-planning"])
planner = TaskPlanner()

@router.post("/plan")
async def plan_task(
    goal: str,
    context: Optional[Dict[str, Any]] = None
) -> TaskPlan:
    """
    Break down a high-level goal into executable steps
    
    Example:
    POST /api/task/plan
    {
        "goal": "Download and organize my project files",
        "context": {
            "active_window": "Chrome",
            "open_apps": ["Explorer", "VSCode"]
        }
    }
    """
    try:
        plan = await planner.plan_task(goal, context or {})
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute")
async def execute_task_plan(plan: TaskPlan) -> Dict[str, Any]:
    """Execute a previously generated task plan"""
    # TODO: Integrate with executor service
    results = await planner.execute_plan(plan, executor)
    return results
```

---

### 4. **Advanced Skill Recording & Playback**

Enhance `Desktop-App/Kernel Agent/Services/SkillRecorder.cs`:

```csharp
// ADD: Conditional logic recording
case "wait_until":
    // Record: "Wait until element 'Save Button' appears or 5 seconds pass"
    break;

case "repeat":
    // Record: "Repeat these 3 actions 5 times"
    break;

case "if_else":
    // Record: "If element exists, click it; otherwise, type text"
    break;

case "loop_through_list":
    // Record: "For each file in Downloads, perform these actions"
    break;

case "extract_text":
    // Record: "Get text from selected element and save to variable"
    break;

case "take_screenshot":
    // Record: "Capture screen at this point for reference"
    break;
```

---

### 5. **Multi-Action Chains (Sequences)**

Create: `Desktop-App/Kernel Agent/Services/ActionChain.cs`

```csharp
using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// Chain multiple actions with conditions and parallel execution
    /// </summary>
    public class ActionChain
    {
        public string ChainId { get; set; }
        public string Name { get; set; }
        public List<ChainStep> Steps { get; set; } = new();
        public bool RunInParallel { get; set; }
        public int RetryCount { get; set; } = 3;

        public async Task<ChainExecutionResult> ExecuteAsync(SmartExecutor executor)
        {
            var result = new ChainExecutionResult { ChainId = ChainId };
            var stepResults = new List<StepResult>();

            if (RunInParallel)
            {
                // Execute all steps in parallel
                var tasks = Steps.Select(step => 
                    ExecuteStepAsync(executor, step));
                var results = await Task.WhenAll(tasks);
                stepResults.AddRange(results);
            }
            else
            {
                // Execute steps sequentially
                foreach (var step in Steps)
                {
                    var stepResult = await ExecuteStepAsync(executor, step);
                    stepResults.Add(stepResult);

                    // Check conditions
                    if (!stepResult.Success && step.StopOnFailure)
                    {
                        result.Success = false;
                        result.Error = $"Step {step.Id} failed, chain stopped";
                        break;
                    }

                    // If step has a conditional next step
                    if (stepResult.Success && !string.IsNullOrEmpty(step.SuccessNextStepId))
                    {
                        // Continue with specified step
                    }
                }
            }

            result.StepResults = stepResults;
            result.Success = stepResults.All(s => s.Success);
            return result;
        }

        private async Task<StepResult> ExecuteStepAsync(SmartExecutor executor, ChainStep step)
        {
            int attempt = 0;
            while (attempt < RetryCount)
            {
                attempt++;
                var result = new StepResult { StepId = step.Id };

                try
                {
                    var actionResult = await executor.ExecuteActionAsync(step.Action);
                    result.Success = actionResult.Success;
                    result.Error = actionResult.Error;
                    result.Attempts = attempt;

                    if (result.Success)
                        break;
                }
                catch (Exception ex)
                {
                    result.Error = ex.Message;
                }

                if (attempt < RetryCount)
                    await Task.Delay(step.RetryDelayMs);
            }

            return result;
        }
    }

    public class ChainStep
    {
        public string Id { get; set; } // Step ID for linking
        public string Description { get; set; }
        public JsonElement Action { get; set; }
        public bool StopOnFailure { get; set; }
        public int RetryDelayMs { get; set; } = 500;
        public string SuccessNextStepId { get; set; } // For conditional branching
        public string FailureNextStepId { get; set; }
    }

    public class ChainExecutionResult
    {
        public string ChainId { get; set; }
        public bool Success { get; set; }
        public string Error { get; set; }
        public List<StepResult> StepResults { get; set; } = new();
    }

    public class StepResult
    {
        public string StepId { get; set; }
        public bool Success { get; set; }
        public string Error { get; set; }
        public int Attempts { get; set; }
    }
}
```

---

## 📝 Usage Examples

### Example 1: File Organization (Using Advanced Actions)
```json
{
  "goal": "Organize my Downloads folder",
  "actions": [
    {"action": "open_app", "target": "explorer.exe"},
    {"action": "navigate", "url": "C:\\Users\\YourName\\Downloads"},
    {"action": "list_files", "path": "C:\\Users\\YourName\\Downloads"},
    {"action": "create_file", "path": "C:\\Users\\YourName\\Downloads\\Documents", "content": ""},
    {"action": "move_file", "source": "*.pdf", "destination": "Documents"}
  ]
}
```

### Example 2: Automated Testing (Using Chains)
```json
{
  "chainId": "web_login_test",
  "name": "Test Website Login",
  "runInParallel": false,
  "steps": [
    {
      "id": "step1",
      "description": "Open Chrome",
      "action": {"action": "open_app", "target": "chrome.exe"}
    },
    {
      "id": "step2",
      "description": "Navigate to login page",
      "action": {"action": "navigate", "url": "https://example.com/login"},
      "stopOnFailure": true
    },
    {
      "id": "step3",
      "description": "Enter username",
      "action": {"action": "type_text", "content": "testuser@example.com"}
    },
    {
      "id": "step4",
      "description": "Wait for password field to load",
      "action": {"action": "wait_for_element", "target": "password field", "timeout_ms": 5000}
    }
  ]
}
```

### Example 3: Autonomous Task (Using Task Planner)
```bash
POST /api/task/plan
{
  "goal": "Download my recent emails and save them as PDFs",
  "context": {
    "active_window": "Outlook",
    "open_apps": ["Outlook", "FileExplorer"]
  }
}

Response:
{
  "goal": "Download my recent emails and save them as PDFs",
  "total_steps": 7,
  "steps": [
    {
      "step_number": 1,
      "description": "Open Outlook if not already open",
      "action": "open_app",
      "target": "outlook.exe"
    },
    {
      "step_number": 2,
      "description": "Click on Inbox to see all emails",
      "action": "click_element",
      "target": "Inbox"
    },
    // ... more steps
  ]
}
```

---

## 🎯 Implementation Roadmap

### Phase 1: Quick Wins (1-2 hours)
- [ ] Add file operations (create, delete, copy, move)
- [ ] Add clipboard operations
- [ ] Add process control (kill, get list)
- [ ] Add window detection

### Phase 2: Vision Enhancements (2-3 hours)
- [ ] Implement `EnhancedVisionEngine.cs`
- [ ] Add fuzzy matching for UI elements
- [ ] Integrate color-based detection
- [ ] Add confidence scoring

### Phase 3: Advanced Planning (3-4 hours)
- [ ] Integrate Task Planner with Gemini
- [ ] Add recovery mechanisms
- [ ] Test with real-world scenarios
- [ ] Add memory for past successful plans

### Phase 4: Automation Chains (2-3 hours)
- [ ] Implement ActionChain system
- [ ] Add parallel execution support
- [ ] Add conditional logic (if/else branching)
- [ ] Create chain recorder UI

---

## 🧪 Testing Commands

```powershell
# Test new advanced actions
Invoke-RestMethod -Uri "http://localhost:5042/api/executor/action" -Method Post -Body @{
    "action" = "list_files"
    "path" = "C:\Users\$env:USERNAME\Downloads"
} -ContentType "application/json"

# Test task planner
Invoke-RestMethod -Uri "http://localhost:8000/api/task/plan" -Method Post -Body @{
    "goal" = "Organize my downloads by file type"
} -ContentType "application/json"
```

---

## 🔒 Security Considerations

When adding file operations and system control:
1. ✅ Use `SecurityPolicyService` to whitelist allowed paths
2. ✅ Validate all file operations against `AllowedPaths`
3. ✅ Log all system commands executed
4. ✅ Implement timeout limits (prevent infinite loops)
5. ✅ Require explicit user approval for critical operations
6. ✅ Sandbox process execution (run in isolated context)

---

## 📚 Integration with Existing Code

### Update SmartExecutor.cs
Add new action handlers to the switch statement in `ExecuteSingleAction()`

### Update Microservice main.py
Register new Task Planner routes:
```python
from app.api import task_planner
app.include_router(task_planner.router)
```

### Update Desktop App Services
Inject `EnhancedVisionEngine` into `SmartExecutor`:
```csharp
public class SmartExecutor
{
    private readonly EnhancedVisionEngine _visionEngine;
    
    public SmartExecutor(..., EnhancedVisionEngine visionEngine)
    {
        _visionEngine = visionEngine;
    }
}
```

---

## 💡 Next Steps

1. **Start with Phase 1** - Add file/process operations (30 mins)
2. **Test thoroughly** - Create test cases for each new action
3. **Document usage** - Add to API documentation
4. **Gather feedback** - See what works best for your use cases
5. **Expand gradually** - Add more advanced features as needed

Good luck making your kernel even more powerful! 🚀
