using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using System.Text;
using KernalAgentBackend.Data;
using DotNetEnv;
using Google.Cloud.Firestore;


// Load .env file (only if it exists - for Docker, use environment variables)
if (File.Exists(".env"))
{
    Env.Load();
}

var builder = WebApplication.CreateBuilder(args);

// CRITICAL: Configure Kestrel to listen on HTTP only (Render handles HTTPS at load balancer)
// Get port from environment or default to 8080
var port = Environment.GetEnvironmentVariable("PORT") ?? "8080";
var httpPort = int.Parse(port);

builder.WebHost.ConfigureKestrel(options =>
{
    // Explicitly bind to HTTP on all interfaces (0.0.0.0)
    // Use Http1 protocol for Render deployment (Render handles HTTPS at load balancer)
    options.ListenAnyIP(httpPort, listenOptions =>
    {
        listenOptions.Protocols = HttpProtocols.Http1;
    });
});

// Add services to the container.
builder.Services.AddControllers();
builder.Services.AddOpenApi();

// Add CORS - Load allowed origins from environment variables
var corsOriginsEnv = Environment.GetEnvironmentVariable("CORS_ALLOWED_ORIGINS");
var allowedOrigins = string.IsNullOrWhiteSpace(corsOriginsEnv)
    ? new[] { "http://localhost:3000", "http://localhost:3001" }
    : corsOriginsEnv.Split(',', StringSplitOptions.RemoveEmptyEntries)
                    .Select(o => o.Trim())
                    .Where(o => !string.IsNullOrWhiteSpace(o))
                    .ToArray();

// Ensure we have at least one origin
if (allowedOrigins.Length == 0)
{
    allowedOrigins = new[] { "http://localhost:3000" };
}

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod();
        // Note: AllowCredentials() removed - not compatible with AllowAnyOrigin()
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

// Add Firestore client
var googleCredentials = Environment.GetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS");
if (string.IsNullOrEmpty(googleCredentials))
{
    throw new InvalidOperationException("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.");
}
var firestoreDb = new FirestoreDbBuilder
{
    ProjectId = "kernal-39125",
    Credential = Google.Apis.Auth.OAuth2.GoogleCredential.FromFile(googleCredentials)
}.Build();
builder.Services.AddSingleton(firestoreDb);


var app = builder.Build();

// Initialize the database
using (var scope = app.Services.CreateScope())
{
    var services = scope.ServiceProvider;
    try
    {
        var context = services.GetRequiredService<ApplicationDbContext>();
        DbInitializer.Initialize(context);

        var firestoreDbInstance = services.GetRequiredService<FirestoreDb>();
        SeedData.SeedUsers(firestoreDbInstance).Wait();
    }
    catch (Exception ex)
    {
        var logger = services.GetRequiredService<ILogger<Program>>();
        logger.LogError(ex, "An error occurred while seeding the database.");
    }
}

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

// CRITICAL: Never use HTTPS redirection in production/container environments
// Render and other cloud platforms handle HTTPS at the load balancer level
// Using HTTPS redirection here causes segmentation faults (Status 139)
// Only enable in local development with actual certificates
var isInContainer = Environment.GetEnvironmentVariable("DOTNET_RUNNING_IN_CONTAINER");
if (app.Environment.IsDevelopment() && 
    (isInContainer == null || !isInContainer.Equals("true", StringComparison.OrdinalIgnoreCase)))
{
    app.UseHttpsRedirection();
}

// Use CORS
app.UseCors("AllowFrontend");

app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

// Kestrel is already configured above, just run the app
// The port binding is handled by ConfigureKestrel
app.Run();
