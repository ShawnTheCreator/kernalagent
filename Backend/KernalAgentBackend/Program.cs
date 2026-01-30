using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using System.Text;
using KernalAgentBackend.Data;
using KernalAgentBackend.Services;
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

// WebSocket manager for device auth (desktop login)
builder.Services.AddSingleton<DeviceAuthWebSocketManager>();

// Add OpenAPI/Swagger support (built-in for .NET 10)
builder.Services.AddEndpointsApiExplorer();

// Add Firestore client
var googleCredentialsPath = Environment.GetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS");
var googleCredentialsJson = Environment.GetEnvironmentVariable("GOOGLE_CREDENTIALS_JSON");

Google.Apis.Auth.OAuth2.GoogleCredential credential;

if (!string.IsNullOrEmpty(googleCredentialsJson))
{
    // Use JSON string from environment variable (for Render/cloud deployments)
    credential = Google.Apis.Auth.OAuth2.GoogleCredential.FromJson(googleCredentialsJson);
}
else if (!string.IsNullOrEmpty(googleCredentialsPath) && File.Exists(googleCredentialsPath))
{
    // Use file path (for local development)
    credential = Google.Apis.Auth.OAuth2.GoogleCredential.FromFile(googleCredentialsPath);
}
else
{
    throw new InvalidOperationException(
        "Either GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS environment variable must be set. " +
        "For cloud deployments, use GOOGLE_CREDENTIALS_JSON with the full JSON content.");
}

var firestoreDb = new FirestoreDbBuilder
{
    ProjectId = "kernal-39125",
    Credential = credential
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

// Enable WebSockets (for desktop auth realtime)
app.UseWebSockets();

app.UseAuthentication();
app.UseAuthorization();

// Realtime auth for desktop app: ws://<host>/ws/auth?deviceId=...
app.Map("/ws/auth", async context =>
{
    if (!context.WebSockets.IsWebSocketRequest)
    {
        context.Response.StatusCode = StatusCodes.Status400BadRequest;
        await context.Response.WriteAsync("WebSocket request required");
        return;
    }

    var deviceId = context.Request.Query["deviceId"].ToString();
    if (string.IsNullOrWhiteSpace(deviceId))
    {
        context.Response.StatusCode = StatusCodes.Status400BadRequest;
        await context.Response.WriteAsync("deviceId query param is required");
        return;
    }

    var wsManager = context.RequestServices.GetRequiredService<DeviceAuthWebSocketManager>();
    using var webSocket = await context.WebSockets.AcceptWebSocketAsync();
    var connectionId = wsManager.Register(deviceId, webSocket);

    try
    {
        var buffer = new byte[1024];
        while (webSocket.State == System.Net.WebSockets.WebSocketState.Open && !context.RequestAborted.IsCancellationRequested)
        {
            var result = await webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), context.RequestAborted);
            if (result.MessageType == System.Net.WebSockets.WebSocketMessageType.Close)
            {
                break;
            }
        }
    }
    finally
    {
        wsManager.Unregister(deviceId, connectionId);
        if (webSocket.State == System.Net.WebSockets.WebSocketState.Open)
        {
            await webSocket.CloseAsync(System.Net.WebSockets.WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
        }
    }
});

app.MapControllers();

// Kestrel is already configured above, just run the app
// The port binding is handled by ConfigureKestrel
app.Run();
