# Complete Render Deployment Guide for Kernal Agent

This guide walks you through deploying all three services (Backend, Microservice, Frontend) to Render.com using the included `render.yaml` blueprint.

## Prerequisites

1. **GitHub Repository**: Push your code to GitHub
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **API Keys Ready**:
   - Gemini API Key (from [Google AI Studio](https://aistudio.google.com/app/apikey))
   - Firebase credentials JSON (if using Firebase)
   - JWT secret key (generate below)

## Quick Deploy (Recommended)

### Option 1: Blueprint Deploy (Fastest)

1. **Connect GitHub to Render**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Select `render.yaml` from the root directory

2. **Set Required Environment Variables**
   
   Render will prompt you to set variables marked as `sync: false`:
   
   **Backend Service:**
   ```
   CORS_ALLOWED_ORIGINS=https://kernalagent-frontend.onrender.com
   GOOGLE_CREDENTIALS_JSON=<paste your Firebase JSON here>
   ```
   
   **Microservice:**
   ```
   GEMINI_API_KEY=AIza...your_key_here
   ```
   
   **Frontend:**
   ```
   NEXT_PUBLIC_API_URL=https://kernalagent-backend.onrender.com/api
   NEXT_PUBLIC_WS_URL=wss://kernalagent-microservice.onrender.com/ws/stream
   ```

3. **Deploy All Services**
   - Click "Apply" to deploy all three services at once
   - Wait 5-10 minutes for initial build

4. **Update Cross-Service URLs**
   - After deployment, you'll get the actual URLs
   - Go back and update the environment variables with real URLs
   - Trigger a manual redeploy for each service

---

## Manual Deploy (Step-by-Step)

If you prefer to deploy services individually:

### 1. Deploy Backend (.NET API)

1. **Create Web Service**
   - Dashboard → "New" → "Web Service"
   - Connect repository
   - Name: `kernalagent-backend`
   
2. **Configuration**
   - **Environment**: Docker
   - **Dockerfile Path**: `Backend/KernalAgentBackend/Dockerfile`
   - **Docker Context**: `Backend/KernalAgentBackend`
   - **Region**: Choose closest to your users

3. **Environment Variables**
   ```
   ASPNETCORE_URLS=http://0.0.0.0:8080
   ASPNETCORE_HTTP_PORTS=8080
   ASPNETCORE_ENVIRONMENT=Production
   DOTNET_RUNNING_IN_CONTAINER=true
   PORT=8080
   JWT_KEY=<generate 64-character key>
   JWT_ISSUER=KernalAgentBackend
   JWT_AUDIENCE=KernalAgentFrontend
   CORS_ALLOWED_ORIGINS=https://kernalagent-frontend.onrender.com
   GOOGLE_CREDENTIALS_JSON=<paste Firebase JSON>
   ```
   
   **Generate JWT Key** (PowerShell):
   ```powershell
   -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for build to complete (~5 min)
   - Note the URL: `https://kernalagent-backend.onrender.com`

5. **Test Backend**
   ```bash
   curl https://kernalagent-backend.onrender.com/
   ```
   Should return API info JSON.

---

### 2. Deploy Microservice (Python/FastAPI)

1. **Create Web Service**
   - Dashboard → "New" → "Web Service"
   - Connect repository
   - Name: `kernalagent-microservice`

2. **Configuration**
   - **Environment**: Docker
   - **Dockerfile Path**: `Microservice/Dockerfile`
   - **Docker Context**: `Microservice`

3. **Environment Variables**
   ```
   GEMINI_API_KEY=AIza...your_key_here
   HOST=0.0.0.0
   PORT=8000
   MODEL_ID=gemini-2.5-flash
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for build (~3-5 min)
   - Note the URL: `https://kernalagent-microservice.onrender.com`

5. **Test Microservice**
   ```bash
   curl https://kernalagent-microservice.onrender.com/health
   ```
   Should return: `{"status":"healthy"}`

---

### 3. Deploy Frontend (Next.js)

1. **Create Web Service**
   - Dashboard → "New" → "Web Service"
   - Connect repository
   - Name: `kernalagent-frontend`

2. **Configuration**
   - **Environment**: Node
   - **Root Directory**: `Frontend`
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm run start`
   - **Node Version**: 20.x

3. **Environment Variables**
   ```
   NODE_ENV=production
   NEXT_PUBLIC_API_URL=https://kernalagent-backend.onrender.com/api
   NEXT_PUBLIC_WS_URL=wss://kernalagent-microservice.onrender.com/ws/stream
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for build (~5 min)
   - Note the URL: `https://kernalagent-frontend.onrender.com`

---

## Post-Deployment Configuration

### Update CORS Origins

After all services are deployed, update the Backend's CORS settings:

1. Go to Backend service → Environment
2. Update `CORS_ALLOWED_ORIGINS`:
   ```
   https://kernalagent-frontend.onrender.com,https://www.your-custom-domain.com
   ```
3. Save and trigger manual deploy

### Configure Desktop App

Update your Desktop App to use production URLs:

1. Edit `.env` in `Desktop-App/Kernel Agent/`:
   ```
   API_BASE_URL=https://kernalagent-backend.onrender.com/api
   ```

2. Or update `ApiService.cs`:
   ```csharp
   private static readonly string API_BASE_URL = 
       "https://kernalagent-backend.onrender.com/api";
   ```

---

## Testing the Full Stack

### 1. Test Authentication Flow

```bash
# Signup
curl -X POST https://kernalagent-backend.onrender.com/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"test123"}'

# Expected: {"token":"eyJ...","user":{...}}
```

### 2. Test AI Microservice

```bash
# Health check
curl https://kernalagent-microservice.onrender.com/health

# Test planning endpoint
curl -X POST https://kernalagent-microservice.onrender.com/api/agent/plan \
  -H "Content-Type: application/json" \
  -d '{"intent":"Open Notepad","screenshot_base64":"..."}'
```

### 3. Test Frontend

1. Visit: `https://kernalagent-frontend.onrender.com`
2. Click "Sign Up" and create account
3. Login and verify dashboard loads
4. Check browser console for any API errors

### 4. Test Desktop App

1. Update Desktop App `.env` with production URL
2. Run the desktop app
3. Login with your account
4. Try a voice command: "Open Notepad"
5. Verify action executes correctly

---

## Troubleshooting

### Backend Returns 503/502

**Issue**: Service not starting properly

**Solution**:
1. Check logs in Render dashboard
2. Verify all environment variables are set
3. Ensure `ASPNETCORE_URLS=http://0.0.0.0:8080`
4. Check Dockerfile exposes correct port

### Microservice Gemini Errors

**Issue**: "API key not valid"

**Solution**:
1. Verify `GEMINI_API_KEY` is set correctly
2. Key should start with `AIza`
3. Check quotas at [Google AI Studio](https://aistudio.google.com/app/apikey)

### Frontend Can't Connect to Backend

**Issue**: CORS errors in browser console

**Solution**:
1. Update Backend's `CORS_ALLOWED_ORIGINS` with exact frontend URL
2. Ensure no trailing slash in URLs
3. Redeploy backend after changing CORS settings

### WebSocket Connection Fails

**Issue**: Desktop app can't connect to microservice WebSocket

**Solution**:
1. Use `wss://` (not `ws://`) for production URLs
2. Ensure firewall allows WebSocket connections
3. Check Render service is running (not sleeping)

### Service Keeps Spinning Down

**Issue**: Free tier services sleep after 15 min inactivity

**Solutions**:
1. Upgrade to paid plan for 24/7 uptime
2. Use external service like [UptimeRobot](https://uptimerobot.com) to ping `/health` every 5 minutes
3. Implement warm-up logic in desktop app

---

## Custom Domain Setup

### Add Custom Domain to Frontend

1. In Render dashboard, go to Frontend service
2. Settings → Custom Domains
3. Add your domain: `app.yourdomain.com`
4. Follow DNS configuration instructions
5. Wait for SSL certificate provisioning (~5 minutes)

### Update All Services

After adding custom domain:

1. **Backend**: Update `CORS_ALLOWED_ORIGINS` with new domain
2. **Frontend**: Update environment variables if needed
3. **Desktop App**: Update `.env` with production domain

---

## Environment Variables Reference

### Backend (Required)

| Variable | Example | Description |
|----------|---------|-------------|
| `ASPNETCORE_URLS` | `http://0.0.0.0:8080` | Forces HTTP binding |
| `ASPNETCORE_HTTP_PORTS` | `8080` | Port number |
| `ASPNETCORE_ENVIRONMENT` | `Production` | Environment mode |
| `JWT_KEY` | `64-char-random-string` | JWT signing key |
| `CORS_ALLOWED_ORIGINS` | `https://app.com` | Allowed origins |
| `GOOGLE_CREDENTIALS_JSON` | `{...}` | Firebase credentials |

### Microservice (Required)

| Variable | Example | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | `AIza...` | Google Gemini API key |
| `HOST` | `0.0.0.0` | Listen address |
| `PORT` | `8000` | Port number |
| `MODEL_ID` | `gemini-2.5-flash` | Model to use |

### Frontend (Required)

| Variable | Example | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://api.com/api` | Backend API URL |
| `NEXT_PUBLIC_WS_URL` | `wss://ws.com/ws/stream` | WebSocket URL |
| `NODE_ENV` | `production` | Node environment |

---

## Monitoring & Logs

### View Real-Time Logs

1. Go to service in Render dashboard
2. Click "Logs" tab
3. Set to "Live" mode
4. Filter by log level (Info, Warning, Error)

### Common Log Patterns

**Healthy Backend:**
```
Now listening on: http://0.0.0.0:8080
Application started. Press Ctrl+C to shut down.
```

**Healthy Microservice:**
```
INFO:     Started server process [1]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Healthy Frontend:**
```
ready - started server on 0.0.0.0:3000
info  - Listening on port 3000
```

---

## Cost Optimization

### Free Tier Limits

- **Web Services**: 750 hours/month (one service 24/7)
- **Build Time**: 500 minutes/month
- **Bandwidth**: 100 GB/month
- **Sleep**: Services sleep after 15 min inactivity

### Strategies for Free Tier

1. **Use Starter Plan for Backend only** ($7/month)
   - Backend stays awake 24/7
   - Microservice can sleep (faster startup)
   - Frontend on free tier (static builds wake fast)

2. **Optimize Build Times**
   - Use Docker layer caching
   - Minimize dependencies in Dockerfile
   - Configure build filters in `render.yaml`

3. **Reduce Cold Starts**
   - Keep health check endpoints lightweight
   - Implement lazy loading in microservice
   - Use persistent connections in desktop app

---

## Advanced Configuration

### Auto-Scaling

Paid plans support auto-scaling. Update `render.yaml`:

```yaml
scaling:
  minInstances: 2
  maxInstances: 10
  targetMemoryPercent: 80
  targetCPUPercent: 70
```

### Background Workers

For janitor agent or background tasks:

```yaml
- type: worker
  name: janitor-worker
  runtime: docker
  dockerfilePath: ./Microservice/Dockerfile
  dockerContext: ./Microservice
  startCommand: python -m app.agents.janitor.daemon
```

### Private Services

If microservice should only be accessed internally:

```yaml
- type: private-service
  name: kernalagent-microservice-private
```

---

## Security Best Practices

1. **Never commit `.env` files** - Use Render's environment variables
2. **Rotate JWT keys regularly** - Update via dashboard
3. **Use HTTPS only** - Render provides free SSL
4. **Restrict CORS origins** - Don't use `*` in production
5. **Enable rate limiting** - Backend already has basic rate limiting
6. **Monitor logs** - Set up alerts for errors
7. **Use secrets management** - Store Firebase JSON as secret file

---

## Support Resources

- **Render Docs**: https://render.com/docs
- **Render Community**: https://community.render.com
- **Project Issues**: Check Backend/RENDER_DEPLOY.md
- **API Status**: https://status.render.com

---

## Next Steps

1. ✅ Deploy all three services
2. ✅ Test authentication flow
3. ✅ Test AI endpoints
4. ✅ Configure desktop app
5. ⏭️ Set up monitoring/alerts
6. ⏭️ Configure custom domain
7. ⏭️ Set up CI/CD automation
8. ⏭️ Implement error tracking (Sentry)

---

## Quick Command Reference

```bash
# Test all services after deployment
curl https://kernalagent-backend.onrender.com/
curl https://kernalagent-microservice.onrender.com/health
curl https://kernalagent-frontend.onrender.com/

# View logs
render logs kernalagent-backend --tail 100

# Trigger manual deploy
render deploy kernalagent-backend

# SSH into service (paid plans)
render ssh kernalagent-backend
```

---

**Deployment Complete!** 🎉

Your Kernal Agent is now running on Render with:
- ✅ Backend API with authentication
- ✅ AI Microservice with Gemini
- ✅ Frontend dashboard
- ✅ Desktop app connectivity

Monitor your services and scale as needed!
