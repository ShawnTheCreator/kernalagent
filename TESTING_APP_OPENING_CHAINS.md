# App Opening & Action Chain Verification Tests
# Run these tests to verify reliability improvements

## Test Suite Overview

This document provides manual and automated tests to verify that app opening and multi-step action chains work accurately and reliably.

## Prerequisites

1. **Backend running** on `http://localhost:5042`
2. **Microservice running** on `http://localhost:8000`
3. **Desktop app running** (C# WinUI client)
4. **Test apps installed**: Notepad, Chrome, Calculator

## Automated Tests

### 1. Run Python Integration Tests

```powershell
cd Microservice
.\venv\Scripts\activate
pytest tests/test_app_opening_chains.py -v
```

Expected: All tests should pass with proper schema validation.

### 2. Run Schema Validation Tests

```powershell
pytest tests/test_schemas.py -v -k "app_opening or action_chain"
```

Expected: Action step schemas validate correctly.

## Manual Desktop App Tests

### Test 1: Simple App Opening

**Command**: "Open Notepad"

**Expected Behavior**:
- ✅ Notepad opens within 2-3 seconds
- ✅ Notepad window is focused and active
- ✅ Cursor is blinking in text area
- ✅ No timeout errors in logs

**Verify**:
- Check Desktop App debug output: `[AUTOMATION] notepad is ready and focused`
- No retry attempts needed (only 1 attempt shown)

### Test 2: Chrome with Profile

**Command**: "Open Chrome"

**Expected Behavior**:
- ✅ Chrome opens with Default profile (no profile picker dialog)
- ✅ Window becomes active within 3-4 seconds
- ✅ Browser is responsive (address bar can be clicked)
- ✅ No manual Enter key press needed

**Verify**:
- Check logs: `[AUTOMATION] Chrome started with --profile-directory=Default`
- Check logs: `[AUTOMATION] Chrome window confirmed and focused`
- Profile picker dialog should NOT appear

### Test 3: App Opening with Retry

**Precondition**: Have Chrome already open, then close it

**Command**: "Open Chrome"

**Expected Behavior**:
- ✅ Detects existing Chrome process
- ✅ Focuses existing window (no new instance)
- ✅ Log shows: `[AUTOMATION] Focused existing app: chrome`
- ✅ No retry needed

### Test 4: Multi-Step Chain (Open + Type)

**Command**: "Open Notepad and type Hello World"

**Expected Behavior**:
- ✅ Notepad opens
- ✅ System waits for Notepad to be ready
- ✅ Text "Hello World" appears in Notepad
- ✅ No characters are dropped
- ✅ No typing happens before Notepad is focused

**Verify**:
- Check logs for: `[EXECUTOR] Tracking last app: notepad`
- Check logs for: `[EXECUTOR] App 'notepad' is focused and ready`
- Text should be complete and accurate

### Test 5: Complex Chain (Search on Web)

**Command**: "Search for GitHub Kernel Agent on Chrome"

**Expected Plan**:
```json
{
  "steps": [
    {"action": "open_app", "target": "chrome.exe"},
    {"action": "navigate", "url": "https://google.com"},
    {"action": "click", "target": "search box"},
    {"action": "type_text", "content": "GitHub Kernel Agent"},
    {"action": "press_key", "key": "enter"}
  ]
}
```

**Expected Behavior**:
- ✅ Chrome opens and navigates to Google
- ✅ Search box is clicked
- ✅ Text is typed completely
- ✅ Enter key submits search
- ✅ Results page loads
- ✅ No race conditions (all actions in correct order)

**Verify**:
- Each action completes before next begins
- Adaptive delays ensure page loads before clicking
- No timeout errors

### Test 6: File Save Dialog Handling

**Command**: "Open Notepad, type Test Document, and save it"

**Expected Behavior**:
- ✅ Notepad opens
- ✅ Text typed: "Test Document"
- ✅ Ctrl+S pressed
- ✅ Save dialog detected automatically
- ✅ Filename entered
- ✅ File saved successfully

**Verify**:
- Check logs: `[EXECUTOR] 🔔 DIALOG DETECTED: 'Save As'`
- Check logs: `[EXECUTOR] Proactive dialog handled`
- File appears in expected location

### Test 7: Rapid Sequential Actions

**Command**: "Open Notepad and type: Line 1, press Enter, Line 2, press Enter, Line 3"

**Expected Behavior**:
- ✅ All 6 actions execute in order
- ✅ No skipped actions
- ✅ Text appears line by line with proper line breaks
- ✅ No concurrency conflicts

**Verify**:
- Execution lock prevents overlapping automation
- Each keystroke registered correctly

### Test 8: App Switching

**Command**: "Open Notepad, type ABC, then open Chrome"

**Expected Behavior**:
- ✅ Notepad opens and receives "ABC"
- ✅ Chrome opens and becomes active window
- ✅ Notepad remains open in background with "ABC" visible
- ✅ Both apps tracked correctly

**Verify**:
- Check logs: `[EXECUTOR] Tracking last app: notepad`
- Check logs: `[EXECUTOR] Tracking last app: chrome`
- Context manager tracks window switches

### Test 9: Recovery on Failure

**Command**: "Open NotExistingApp"

**Expected Behavior**:
- ✅ System attempts to open app (retries 3 times with backoff)
- ✅ After all retries fail, vision recovery is called
- ✅ User notified of failure with clear error message
- ✅ No infinite loops or hangs

**Verify**:
- Check logs: `[AUTOMATION] Attempt 1/3...`
- Check logs: `[AUTOMATION] Retry after 100ms...`
- Check logs: `[EXECUTOR] Action failed: open_app, attempting vision recovery...`

### Test 10: Stress Test (Long Chain)

**Command**: "Open Notepad and type the numbers 1 to 10 with Enter after each"

**Expected Plan**: 20+ actions (type + enter × 10)

**Expected Behavior**:
- ✅ All 10 numbers typed
- ✅ All 10 Enter keys pressed
- ✅ No timeouts despite long chain
- ✅ Execution completes within reasonable time (< 30 seconds)
- ✅ Semaphore lock prevents concurrent execution if another command comes in

**Verify**:
- Check final text has all numbers 1-10 on separate lines
- No dropped actions

## Performance Benchmarks

### App Opening Times (Targets)

| App | First Open | Focus Existing | Max Acceptable |
|-----|------------|----------------|----------------|
| Notepad | < 2s | < 0.5s | 5s |
| Chrome | < 4s | < 1s | 8s |
| Calculator | < 1.5s | < 0.5s | 4s |
| VS Code | < 6s | < 2s | 12s |

### Action Chain Timings

| Chain Type | Steps | Target Time | Max Acceptable |
|------------|-------|-------------|----------------|
| Simple (app + type) | 2 | < 3s | 6s |
| Medium (app + nav + click) | 3-5 | < 8s | 15s |
| Complex (multi-app) | 6-10 | < 15s | 30s |
| Long chain | 20+ | < 40s | 60s |

## Verification Checklist

After running all tests, verify these improvements are working:

### ✅ Reliability Improvements

- [ ] Apps open successfully 95%+ of the time
- [ ] Retry logic activates on transient failures
- [ ] Chrome opens without profile picker appearing
- [ ] Window focus is verified before typing
- [ ] All actions execute in correct sequence

### ✅ Timing Improvements

- [ ] Adaptive delays reduce total execution time by ~30%
- [ ] System waits only as long as needed (not fixed delays)
- [ ] No premature actions (typing before window ready)
- [ ] Inter-action delays appropriate for action type

### ✅ Synchronization Improvements

- [ ] Semaphore lock prevents concurrent automation
- [ ] No race conditions in rapid sequences
- [ ] Window handle stability checked (2 consecutive stable checks)
- [ ] Focus verification ensures correct active window

### ✅ Error Handling

- [ ] Failed app opens retry with exponential backoff
- [ ] Vision recovery activates after retries exhausted
- [ ] Dialog detection works proactively
- [ ] Clear error messages on permanent failures

### ✅ Logging & Observability

- [ ] Retry attempts logged with attempt number
- [ ] Timing information included in logs
- [ ] App focus verification logged
- [ ] Adaptive delay outcomes logged

## Debugging Tips

### Issue: App opens but typing fails

**Check**:
- Look for: `[EXECUTOR] Warning: Could not verify '<app>' is focused`
- Solution: Increase `VerifyAppReadyForInput` max attempts

### Issue: Chrome profile picker still appears

**Check**:
- Verify Chrome version supports `--profile-directory`
- Check logs for: `[AUTOMATION] Chrome started with --profile-directory=Default`
- Try deleting Chrome cache and restart

### Issue: Actions execute too slowly

**Check**:
- Look for: `[EXECUTOR] Max delay reached: 5000ms`
- System may be under load
- Check `IsSystemReady()` is returning true

### Issue: Concurrent execution errors

**Check**:
- Look for multiple `[EXECUTOR] Plan completed` messages overlapping
- Semaphore should prevent this
- Verify `_executionLock` is static singleton

### Issue: Retry loop infinite

**Check**:
- Verify `maxRetries = 3` in OpenApplication
- Check exponential backoff is working: `100ms, 200ms, 400ms`
- Ensure final retry returns false

## Success Criteria

All tests passing means:

✅ **Reliability**: 95%+ success rate on app opening
✅ **Timing**: Actions execute with optimal delays (not too fast, not too slow)
✅ **Synchronization**: No race conditions or concurrent conflicts
✅ **Recovery**: System recovers gracefully from failures
✅ **User Experience**: Commands feel responsive and accurate

## Next Steps

If any tests fail, check:

1. **Logs** - Desktop App debug output in Visual Studio
2. **Microservice** - FastAPI logs at `http://localhost:8000`
3. **Network** - WebSocket connection stable
4. **System** - Windows not under heavy load
5. **Dependencies** - All NuGet packages updated

Report issues with:
- Test name that failed
- Expected vs actual behavior  
- Relevant log excerpts
- System state (apps open, CPU usage, etc.)
