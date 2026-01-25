# Required Render Environment Variables

## Critical Variables (Must Set)

These variables **MUST** be set in your Render dashboard to prevent Status 139 errors:

| Key | Value | Why It's Critical |
|-----|-------|-------------------|
| `ASPNETCORE_URLS` | `http://0.0.0.0:8080` | Forces HTTP binding on all interfaces |
| `ASPNETCORE_HTTP_PORTS` | `8080` | Explicitly tells .NET 10 to use port 8080 |
| `ASPNETCORE_ENVIRONMENT` | `Production` | Disables dev features that look for SSL certs |
| `DOTNET_RUNNING_IN_CONTAINER` | `true` | Tells .NET it's in a container (disables HTTPS) |
| `PORT` | `8080` | Render's port variable (if used) |

## Application Variables

| Key | Value | Required |
|-----|-------|----------|
| `JWT_KEY` | Your secret key (64+ chars) | ✅ Yes |
| `JWT_ISSUER` | `KernalAgentBackend` | Optional |
| `JWT_AUDIENCE` | `KernalAgentFrontend` | Optional |
| `CORS_ALLOWED_ORIGINS` | `https://your-frontend.onrender.com` | ✅ Yes (specific URLs, not wildcard) |
| `DATABASE_CONNECTION_STRING` | Your DB connection | If using SQL Server |

## Quick Copy-Paste for Render

```
ASPNETCORE_URLS=http://0.0.0.0:8080
ASPNETCORE_HTTP_PORTS=8080
ASPNETCORE_ENVIRONMENT=Production
DOTNET_RUNNING_IN_CONTAINER=true
PORT=8080
JWT_KEY=YourSuperSecretKeyThatShouldBeAtLeast32CharactersLong!
CORS_ALLOWED_ORIGINS=https://your-frontend.onrender.com
```

## Why These Variables Matter

1. **ASPNETCORE_URLS**: Prevents .NET from reading `launchSettings.json` and trying to bind to HTTPS
2. **ASPNETCORE_HTTP_PORTS**: Explicitly tells .NET 10 which port to use for HTTP
3. **DOTNET_RUNNING_IN_CONTAINER**: Disables certificate lookups and HTTPS features
4. **ASPNETCORE_ENVIRONMENT=Production**: Disables developer exception pages that may trigger HTTPS

## Testing After Setting Variables

1. Redeploy your service in Render
2. Check logs - should see: `Now listening on: http://0.0.0.0:8080`
3. Test endpoint: `curl https://your-app.onrender.com/`
4. Should return JSON, not Status 139

