# Kernel Architecture Testing Guide

## Prerequisites

1. **Ollama running locally** with `gemma:2b` model:
   ```bash
   # Install Ollama if not already installed
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull and start Gemma model
   ollama pull gemma:2b
   ollama serve
   ```

2. **Gemini API key** set in microservice `.env`:
   ```
   GEMINI_API_KEY=AIza... (your key)
   ```

3. **All services running**:
   - Backend (.NET API)
   - Microservice (Python/FastAPI)
   - Desktop App (C# WinUI)

## Testing Steps

### 1. Verify Microservice Endpoints

#### Test Gemma Interpreter
```bash
curl -X POST "http://localhost:8000/api/kernel/interpret" \
  -H "Content-Type: application/json" \
  -d '{"command": "open notepad and type hello"}'
```

Expected response:
```json
{
  "intent": "file_operation",
  "entities": ["notepad", "hello"],
  "capabilities": ["open_application", "text_input"],
  "confidence": 0.85,
  "risk": "low"
}
```

#### Test Gemini Planner
```bash
curl -X POST "http://localhost:8000/api/kernel/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "open notepad and type hello",
    "interpretation": {
      "intent": "file_operation",
      "entities": ["notepad", "hello"],
      "capabilities": ["open_application", "text_input"],
      "confidence": 0.85,
      "risk": "low"
    }
  }'
```

Expected response:
```json
{
  "confidence": 0.9,
  "steps": [
    {
      "action": "CLICK",
      "coordinate_label": null,
      "text_payload": "notepad",
      "requires_vision_targeting": false
    },
    {
      "action": "TYPE",
      "coordinate_label": null,
      "text_payload": "hello",
      "requires_vision_targeting": false
    }
  ]
}
```

### 2. Test Desktop App Integration

#### Method 1: Voice Command
1. Run Desktop App
2. Click voice button and say: *"open notepad and type hello"*
3. Check debug output for:
   - Gemma interpretation call
   - Gemini plan call
   - Execution steps

#### Method 2: Manual Command Entry
Add temporary test button in MainWindow.xaml.cs:
```csharp
private async void TestButton_Click(object sender, RoutedEventArgs e)
{
    var testCommand = "open calculator";
    var result = await KernelOrchestrator.Instance.RunAsync(
        testCommand, 
        new SmartExecutor(), 
        null
    );
    
    System.Diagnostics.Debug.WriteLine($"Result: {result.AgentText}");
    System.Diagnostics.Debug.WriteLine($"Success: {result.ExecutionSuccess}");
}
```

### 3. Verify Memory System

#### Check Log Files
After executing commands, check:
```
Desktop-App/Kernel Agent/logs/execution_traces.jsonl
Desktop-App/Kernel Agent/logs/capability_patterns.json
```

#### Test Memory API
```bash
# Get patterns
curl "http://localhost:8000/api/memory/patterns"

# Get stats
curl "http://localhost:8000/api/memory/stats"
```

### 4. Debug Monitoring

#### Microservice Logs
Check microservice console for:
- `[KERNEL-INTERPRET]` messages
- `[KERNEL-PLAN]` messages
- Ollama HTTP calls

#### Desktop App Debug Output
Look for:
- `[KERNEL]` orchestrator messages
- `[API]` service calls
- Execution timing

## Common Issues & Solutions

### Issue 1: Gemma Connection Failed
**Symptoms**: Interpreter returns stub data
**Solution**:
1. Verify Ollama is running: `curl http://localhost:11434/api/tags`
2. Check model: `ollama list`
3. Verify environment variables in microservice

### Issue 2: Gemini API Errors
**Symptoms**: Planner returns error
**Solution**:
1. Check API key validity
2. Verify network connectivity
3. Check microservice .env file

### Issue 3: Desktop App Build Errors
**Symptoms**: Compilation fails
**Solution**:
1. Check namespaces in KernelOrchestrator.cs
2. Verify SafeMemoryLogger.cs is included in project
3. Run `dotnet clean` then `dotnet build`

### Issue 4: No Execution
**Symptoms**: Plan generated but no action
**Solution**:
1. Check SmartExecutor integration
2. Verify coordinate targeting
3. Check UI element detection

## Performance Testing

### Test Commands to Try
1. **Simple**: "open calculator"
2. **Complex**: "open notepad, type hello world, save as test.txt"
3. **Vision**: "click on any video on youtube"
4. **Multi-step**: "open chrome, go to google.com, search for kernel agent"

### Measure Metrics
- Interpretation time (Gemma)
- Planning time (Gemini)
- Execution time (SmartExecutor)
- Total end-to-end time
- Success rate

## Automated Testing Script

```powershell
# test-kernel.ps1
Write-Host "Testing Kernel Architecture..."

# Test 1: Gemma Interpreter
Write-Host "Test 1: Gemma Interpreter"
$response = curl -s -X POST "http://localhost:8000/api/kernel/interpret" `
  -H "Content-Type: application/json" `
  -d '{"command": "open calculator"}'
Write-Host $response

# Test 2: Gemini Planner
Write-Host "Test 2: Gemini Planner"
$interpretation = $response | ConvertFrom-Json
$planResponse = curl -s -X POST "http://localhost:8000/api/kernel/plan" `
  -H "Content-Type: application/json" `
  -d @{
    command = "open calculator"
    interpretation = $interpretation
  } | ConvertTo-Json -Depth 10
Write-Host $planResponse

# Test 3: Memory Stats
Write-Host "Test 3: Memory Stats"
$stats = curl -s "http://localhost:8000/api/memory/stats"
Write-Host $stats

Write-Host "Testing complete!"
```

## Success Criteria

✅ **Architecture Working**:
- Gemma returns valid interpretation JSON
- Gemini returns valid plan JSON
- Desktop App executes commands successfully
- Memory system stores execution traces

✅ **Performance Acceptable**:
- Interpretation < 2 seconds
- Planning < 5 seconds
- Execution varies by complexity

✅ **No Regressions**:
- Existing voice commands still work
- UI remains responsive
- Error handling works gracefully

Run this test suite to verify the new Kernel Architecture is working correctly!
