using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using System.Text;
using KernalAgentBackend.Data;
using DotNetEnv;

// Load .env file (only if it exists - for Docker, use environment variables)
if (File.Exists(".env"))
{
    Env.Load();
}

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllers();
builder.Services.AddOpenApi();

// Add CORS - Load allowed origins from environment variables
var allowedOrigins = Environment.GetEnvironmentVariable("CORS_ALLOWED_ORIGINS")?.Split(',')
    ?? new[] { "http://localhost:3000", "http://localhost:3001" };

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.WithOrigins(allowedOrigins)
              .AllowAnyHeader()
              .AllowAnyMethod()
              .AllowCredentials();
    });
});

// Add Entity Framework
builder.Services.AddDbContext<ApplicationDbContext>(options =>
{
    var connectionString = Environment.GetEnvironmentVariable("DATABASE_CONNECTION_STRING");
    
    if (string.IsNullOrEmpty(connectionString))
    {
        // Use InMemory database for development if no connection string is provided
        options.UseInMemoryDatabase("KernalAgentDb");
    }
    else
    {
        // Use SQL Server if connection string is provided
        options.UseSqlServer(connectionString);
    }
});

// Add JWT Authentication - Load from environment variables
var jwtKey = Environment.GetEnvironmentVariable("JWT_KEY") 
    ?? throw new InvalidOperationException("JWT_KEY environment variable is required");
var jwtIssuer = Environment.GetEnvironmentVariable("JWT_ISSUER") ?? "KernalAgentBackend";
var jwtAudience = Environment.GetEnvironmentVariable("JWT_AUDIENCE") ?? "KernalAgentFrontend";

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = jwtIssuer,
            ValidAudience = jwtAudience,
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey))
        };
    });

builder.Services.AddAuthorization();

// Add OpenAPI/Swagger support (built-in for .NET 10)
builder.Services.AddEndpointsApiExplorer();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

// Only use HTTPS redirection in development (cloud platforms handle HTTPS at load balancer)
if (app.Environment.IsDevelopment())
{
    app.UseHttpsRedirection();
}

// Use CORS
app.UseCors("AllowFrontend");

app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

// Get port from environment variable (for cloud platforms like Render)
var port = Environment.GetEnvironmentVariable("PORT") ?? "8080";
var urls = $"http://0.0.0.0:{port}";

app.Run(urls);
