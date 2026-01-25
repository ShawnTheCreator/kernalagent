# Deploying to Render.com

This guide explains how to deploy KernalAgentBackend to Render.com.

## Why HTTP Only?

Render (and most cloud platforms) handle HTTPS at the **load balancer/reverse proxy level**. Your container should only listen on **HTTP** (port 8080). Render will:
1. Receive HTTPS requests from users
2. Decrypt them at the load balancer
3. Forward HTTP requests to your container

## Render Configuration

### 1. Environment Variables in Render Dashboard

Go to your Render service → Environment tab and add:

| Key | Value | Required |
|-----|-------|----------|
| `ASPNETCORE_URLS` | `http://0.0.0.0:8080` | ✅ Yes |
| `ASPNETCORE_HTTP_PORTS` | `8080` | ✅ Yes |
| `PORT` | `8080` | ✅ Yes |
| `ASPNETCORE_ENVIRONMENT` | `Production` | Recommended |
| `JWT_KEY` | `YourSuperSecretKey...` | ✅ Yes |
| `JWT_ISSUER` | `KernalAgentBackend` | Optional |
| `JWT_AUDIENCE` | `KernalAgentFrontend` | Optional |
| `DATABASE_CONNECTION_STRING` | Your DB connection | If using SQL Server |
| `CORS_ALLOWED_ORIGINS` | `https://your-frontend.onrender.com` | ✅ Yes (for production) |

### 2. Render Service Settings

- **Build Command**: `dotnet publish -c Release -o ./publish`
- **Start Command**: `dotnet ./publish/KernalAgentBackend.dll`
- **Dockerfile Path**: `Dockerfile` (if using Docker)
- **Port**: `8080`

### 3. Using Docker on Render

If deploying with Docker:

1. **Dockerfile Path**: `Backend/KernalAgentBackend/Dockerfile`
2. **Root Directory**: `Backend/KernalAgentBackend`
3. **Port**: `8080`

## Quick Deploy Steps

### Option A: Docker Deploy

1. Connect your GitHub repo to Render
2. Create new **Web Service**
3. Select your repository
4. Set:
   - **Name**: `kernalagent-backend`
   - **Environment**: `Docker`
   - **Dockerfile Path**: `Backend/KernalAgentBackend/Dockerfile`
   - **Root Directory**: `Backend/KernalAgentBackend`
5. Add environment variables (see table above)
6. Click **Create Web Service**

### Option B: Buildpack Deploy

1. Create new **Web Service**
2. Set:
   - **Build Command**: `cd Backend/KernalAgentBackend && dotnet publish -c Release -o ./publish`
   - **Start Command**: `cd Backend/KernalAgentBackend && dotnet ./publish/KernalAgentBackend.dll`
3. Add environment variables
4. Deploy

## Testing After Deploy

### 1. Check Health Endpoint

```bash
curl https://your-app.onrender.com/
```

Should return JSON with API information.

### 2. Test Signup

```bash
curl -X POST https://your-app.onrender.com/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"test123"}'
```

### 3. Update Desktop App

Update `ApiService.cs` in your desktop app:

```csharp
private static readonly string API_BASE_URL = 
    Environment.GetEnvironmentVariable("API_BASE_URL") 
    ?? "https://your-app.onrender.com/api";
```

Or set `API_BASE_URL` environment variable in desktop app's `.env`:

```
API_BASE_URL=https://your-app.onrender.com/api
```

## Common Issues

### Issue: "Unable to configure HTTPS endpoint"

**Solution**: Make sure these environment variables are set:
- `ASPNETCORE_URLS=http://0.0.0.0:8080`
- `ASPNETCORE_HTTP_PORTS=8080`
- `PORT=8080`

### Issue: "Connection refused" from desktop app

**Solution**: 
1. Check Render service is running (green status)
2. Verify CORS settings include your desktop app's origin
3. Check firewall/network settings

### Issue: Database connection fails

**Solution**:
- For production, use external database (Render PostgreSQL, Azure SQL, etc.)
- Set `DATABASE_CONNECTION_STRING` environment variable
- Don't use InMemory database in production!

## Production Checklist

- [ ] Environment variables set in Render
- [ ] `ASPNETCORE_URLS=http://0.0.0.0:8080` is set
- [ ] `JWT_KEY` is a strong, random value
- [ ] `CORS_ALLOWED_ORIGINS` includes production frontend URL
- [ ] Database connection string configured (if using SQL Server)
- [ ] Service is running and healthy
- [ ] Desktop app `API_BASE_URL` updated to Render URL
- [ ] Tested signup/login endpoints

## Security Notes

1. **Never commit `.env` files** - Use Render's environment variables
2. **Use strong JWT keys** - Generate random 64+ character strings
3. **Update CORS** - Remove localhost origins in production
4. **Use HTTPS** - Render provides this automatically
5. **Database security** - Use connection strings with proper authentication

## Monitoring

Render provides:
- **Logs**: View in Render dashboard
- **Metrics**: CPU, Memory usage
- **Health checks**: Automatic monitoring

Check logs if you encounter issues:
```bash
# In Render dashboard → Logs tab
```

## Next Steps

1. Deploy backend to Render
2. Update desktop app to use Render URL
3. Test authentication flow
4. Set up production database (if needed)
5. Configure monitoring and alerts

