using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using KernalAgentBackend.Data;
using KernalAgentBackend.DTOs;
using KernalAgentBackend.Models;
using DbUser = KernalAgentBackend.Models.User;
using BCrypt.Net;

namespace KernalAgentBackend.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly ApplicationDbContext _context;
    private readonly IConfiguration _configuration;

    private readonly FirestoreDb _firestoreDb;

    public AuthController(ApplicationDbContext context, IConfiguration configuration, FirestoreDb firestoreDb)
    {
        _context = context;
        _configuration = configuration;
        _firestoreDb = firestoreDb;
    }

    [HttpPost("signup")]
    public async Task<ActionResult<AuthResponse>> Signup([FromBody] SignupRequest request)
    {
        // Validate input
        if (string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.Password) || string.IsNullOrWhiteSpace(request.Name))
        {
            return BadRequest(new { message = "Name, email, and password are required" });
        }

        // Check if user already exists
        if (await _context.Users.AnyAsync(u => u.Email == request.Email))
        {
            return Conflict(new { message = "User with this email already exists" });
        }

        // Validate email format
        if (!request.Email.Contains('@') || !request.Email.Contains('.'))
        {
            return BadRequest(new { message = "Invalid email format" });
        }

        // Validate password length
        if (request.Password.Length < 6)
        {
            return BadRequest(new { message = "Password must be at least 6 characters" });
        }

        // Hash password
        var passwordHash = BCrypt.Net.BCrypt.HashPassword(request.Password);

        // Create user
        var user = new DbUser
        {
            Name = request.Name,
            Email = request.Email,
            PasswordHash = passwordHash,
            CreatedAt = DateTime.UtcNow
        };

        _context.Users.Add(user);
        await _context.SaveChangesAsync();

        // Also store user in Firestore
        try
        {
            var userDoc = new {
                Email = user.Email,
                CreatedAt = Timestamp.FromDateTime(DateTime.UtcNow),
                NeuralCredits = 0,
                Name = user.Name
            };
            await _firestoreDb.Collection("users").Document(user.Id.ToString()).SetAsync(userDoc);
        }
        catch (Exception ex)
        {
            // Optionally log error but do not block signup
        }

        // Generate token
        var token = GenerateJwtToken(user);

        return Ok(new AuthResponse
        {
            Token = token,
            User = new UserDto
            {
                Id = user.Id,
                Name = user.Name,
                Email = user.Email
            }
        });
    }

    [HttpPost("login")]
    public async Task<ActionResult<AuthResponse>> Login([FromBody] LoginRequest request)
    {
        // Validate input
        if (string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.Password))
        {
            return BadRequest(new { message = "Email and password are required" });
        }

        // Find user
        var user = await _context.Users.FirstOrDefaultAsync(u => u.Email == request.Email);
        if (user == null)
        {
            return Unauthorized(new { message = "Invalid email or password" });
        }

        // Verify password
        if (!BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
        {
            return Unauthorized(new { message = "Invalid email or password" });
        }

        // Generate token
        var token = GenerateJwtToken(user);

        return Ok(new AuthResponse
        {
            Token = token,
            User = new UserDto
            {
                Id = user.Id,
                Name = user.Name,
                Email = user.Email
            }
        });
    }

    [HttpGet("me")]
    public async Task<ActionResult<UserDto>> GetCurrentUser()
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        if (userIdClaim == null || !int.TryParse(userIdClaim, out var userId))
        {
            return Unauthorized(new { message = "Invalid token" });
        }

        var user = await _context.Users.FindAsync(userId);
        if (user == null)
        {
            return NotFound(new { message = "User not found" });
        }

        return Ok(new UserDto
        {
            Id = user.Id,
            Name = user.Name,
            Email = user.Email
        });
    }

    private string GenerateJwtToken(DbUser user)
    {
        var jwtKey = Environment.GetEnvironmentVariable("JWT_KEY") 
            ?? throw new InvalidOperationException("JWT_KEY environment variable is required");
        var jwtIssuer = Environment.GetEnvironmentVariable("JWT_ISSUER") ?? "KernalAgentBackend";
        var jwtAudience = Environment.GetEnvironmentVariable("JWT_AUDIENCE") ?? "KernalAgentFrontend";

        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
            new Claim(ClaimTypes.Email, user.Email),
            new Claim(ClaimTypes.Name, user.Name)
        };

        var token = new JwtSecurityToken(
            issuer: jwtIssuer,
            audience: jwtAudience,
            claims: claims,
            expires: DateTime.UtcNow.AddDays(7),
            signingCredentials: creds
        );

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}

