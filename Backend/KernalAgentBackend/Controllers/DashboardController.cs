using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using KernalAgentBackend.Data;
using System.Security.Claims;

namespace KernalAgentBackend.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class DashboardController : ControllerBase
{
    private readonly ApplicationDbContext _context;

    public DashboardController(ApplicationDbContext context)
    {
        _context = context;
    }

    [HttpGet("skills")]
    public async Task<ActionResult> GetSkills()
    {
        // Mock skills data - replace with actual database queries later
        var skills = new[]
        {
            new { id = "1", name = "Open Application", description = "Launch any installed application by name", confidence = "high", lastExecuted = DateTime.UtcNow.AddMinutes(-1), executionCount = 347 },
            new { id = "2", name = "Type Text", description = "Enter text into focused input fields", confidence = "high", lastExecuted = DateTime.UtcNow.AddMinutes(-2), executionCount = 892 },
            new { id = "3", name = "Click Element", description = "Click on screen elements by visual recognition", confidence = "high", lastExecuted = DateTime.UtcNow.AddSeconds(-30), executionCount = 1243 },
            new { id = "4", name = "Scroll Page", description = "Scroll within windows and web pages", confidence = "medium", lastExecuted = DateTime.UtcNow.AddMinutes(-5), executionCount = 156 },
            new { id = "5", name = "Navigate Tabs", description = "Switch between browser tabs and windows", confidence = "medium", lastExecuted = DateTime.UtcNow.AddMinutes(-10), executionCount = 89 },
            new { id = "6", name = "Fill Form", description = "Automatically populate form fields", confidence = "medium", lastExecuted = DateTime.UtcNow.AddHours(-1), executionCount = 34 },
            new { id = "7", name = "Screenshot Analysis", description = "Extract information from screen captures", confidence = "high", lastExecuted = DateTime.UtcNow.AddSeconds(-45), executionCount = 567 },
            new { id = "8", name = "File Management", description = "Create, move, and organize files", confidence = "low", lastExecuted = DateTime.UtcNow.AddDays(-1), executionCount = 12 },
        };

        return Ok(skills);
    }

    [HttpGet("activities")]
    public async Task<ActionResult> GetActivities()
    {
        // Mock activities - replace with actual database queries later
        var activities = new[]
        {
            new { id = Guid.NewGuid().ToString(), state = "EXECUTING", title = "Opening Notepad", description = "Launching application to write document", timestamp = DateTime.UtcNow.AddSeconds(-10), isNew = false },
            new { id = Guid.NewGuid().ToString(), state = "THINKING", title = "Analyzing request", description = "Processing user intent and planning action sequence", timestamp = DateTime.UtcNow.AddSeconds(-20), isNew = false },
            new { id = Guid.NewGuid().ToString(), state = "OBSERVING", title = "Reading screen content", description = "Capturing current window state", timestamp = DateTime.UtcNow.AddSeconds(-30), isNew = false },
            new { id = Guid.NewGuid().ToString(), state = "PLANNING", title = "Determining next steps", description = "Building execution plan for task completion", timestamp = DateTime.UtcNow.AddSeconds(-40), isNew = false },
            new { id = Guid.NewGuid().ToString(), state = "EXECUTING", title = "Clicking save button", description = "Executing mouse click at coordinates (842, 156)", timestamp = DateTime.UtcNow.AddSeconds(-50), isNew = false },
            new { id = Guid.NewGuid().ToString(), state = "EXECUTING", title = "Typing content", description = "Entering text into active field", timestamp = DateTime.UtcNow.AddSeconds(-60), isNew = false },
        };

        return Ok(activities);
    }

    [HttpGet("metrics")]
    public async Task<ActionResult> GetMetrics()
    {
        // Mock metrics - replace with actual database queries later
        var metrics = new
        {
            tasksPerHour = new[] { 12, 8, 15, 22, 18, 24, 31, 28, 19, 14, 16, 21, 25, 23, 17, 20, 26, 29, 33, 27, 22, 18, 15, 11 },
            latencyMs = new[] { 45, 42, 48, 51, 39, 44, 47, 52, 41, 38, 43, 46, 49, 44, 40, 42, 45, 48, 51, 47, 43, 41, 39, 42 },
            successRate = new[] { 100, 98, 99, 97, 100, 99, 98, 99, 100, 98, 99, 100, 97, 99, 100, 98, 99, 100, 98, 99, 100, 99, 98, 100 },
        };

        return Ok(metrics);
    }

    [HttpGet("stats")]
    public async Task<ActionResult> GetStats()
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        if (userIdClaim == null || !int.TryParse(userIdClaim, out var userId))
        {
            return Unauthorized();
        }

        // Mock stats - replace with actual database queries later
        var stats = new
        {
            totalTasks = 1247,
            successRate = 98.5,
            averageLatency = 45,
            uptime = "2h 34m",
            activeSkills = 8
        };

        return Ok(stats);
    }
}

