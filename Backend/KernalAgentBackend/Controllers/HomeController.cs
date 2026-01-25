using Microsoft.AspNetCore.Mvc;

namespace KernalAgentBackend.Controllers;

[ApiController]
[Route("/")]
public class HomeController : ControllerBase
{
    [HttpGet]
    public IActionResult Get()
    {
        return Ok(new
        {
            message = "Kernal Agent Backend API",
            version = "1.0.0",
            endpoints = new
            {
                openapi = "/openapi/v1.json",
                auth = new
                {
                    signup = "/api/auth/signup",
                    login = "/api/auth/login",
                    me = "/api/auth/me"
                },
                dashboard = new
                {
                    skills = "/api/dashboard/skills",
                    activities = "/api/dashboard/activities",
                    metrics = "/api/dashboard/metrics",
                    stats = "/api/dashboard/stats"
                }
            }
        });
    }
}

