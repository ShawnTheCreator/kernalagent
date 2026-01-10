# Docker Deployment Guide for KernalAgentBackend

This guide explains how to containerize and deploy the KernalAgentBackend using Docker.

## Prerequisites

- Docker Desktop installed (or Docker Engine on Linux)
- Docker Compose (usually included with Docker Desktop)
- .NET 10.0 SDK (for building locally, optional)

## Quick Start

### 1. Build and Run with Docker Compose

```powershell
cd Backend\KernalAgentBackend

# Build and start the container
docker-compose up --build
```

The backend will be available at `http://localhost:5042`

### 2. Run in Background (Detached Mode)

```powershell
docker-compose up -d --build
```

### 3. View Logs

```powershell
docker-compose logs -f kernalagent-backend
```

### 4. Stop the Container

```powershell
docker-compose down
```

## Environment Variables

Create a `.env` file in the `Backend\KernalAgentBackend` directory:

```env
JWT_KEY=YourSuperSecretKeyThatShouldBeAtLeast32CharactersLong!ChangeThisInProduction
JWT_ISSUER=KernalAgentBackend
JWT_AUDIENCE=KernalAgentFrontend
DATABASE_CONNECTION_STRING=
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

**Important:** The `.env` file is already in `.gitignore` - never commit it!

## Building the Docker Image

### Build Only

```powershell
docker build -t kernalagent-backend:latest .
```

### Build with Custom Tag

```powershell
docker build -t kernalagent-backend:v1.0.0 .
```

## Running the Container

### Basic Run

```powershell
docker run -d \
  -p 5042:8080 \
  -e JWT_KEY="YourSuperSecretKeyThatShouldBeAtLeast32CharactersLong!" \
  -e JWT_ISSUER="KernalAgentBackend" \
  -e JWT_AUDIENCE="KernalAgentFrontend" \
  --name kernalagent-backend \
  kernalagent-backend:latest
```

### Run with Environment File

```powershell
docker run -d \
  -p 5042:8080 \
  --env-file .env \
  --name kernalagent-backend \
  kernalagent-backend:latest
```

## Production Deployment

### Using Production Compose File

```powershell
docker-compose -f docker-compose.prod.yml up -d --build
```

### Production Environment Variables

For production, set these environment variables:

```env
ASPNETCORE_ENVIRONMENT=Production
JWT_KEY=<strong-secure-key>
DATABASE_CONNECTION_STRING=<your-production-db-connection-string>
CORS_ALLOWED_ORIGINS=<your-production-frontend-urls>
```

## Docker Commands Reference

### View Running Containers

```powershell
docker ps
```

### View All Containers (Including Stopped)

```powershell
docker ps -a
```

### View Container Logs

```powershell
docker logs kernalagent-backend
docker logs -f kernalagent-backend  # Follow logs
```

### Stop Container

```powershell
docker stop kernalagent-backend
```

### Remove Container

```powershell
docker rm kernalagent-backend
```

### Remove Image

```powershell
docker rmi kernalagent-backend:latest
```

### Execute Commands in Container

```powershell
docker exec -it kernalagent-backend /bin/bash
```

## Troubleshooting

### Container Won't Start

1. Check logs:
   ```powershell
   docker logs kernalagent-backend
   ```

2. Verify environment variables:
   ```powershell
   docker exec kernalagent-backend env
   ```

3. Check if port is already in use:
   ```powershell
   netstat -ano | findstr :5042
   ```

### JWT_KEY Error

If you see "JWT_KEY environment variable is required":
- Make sure `.env` file exists
- Or pass `JWT_KEY` as environment variable
- Check docker-compose.yml has the environment variable set

### Database Connection Issues

- If using InMemory database: No connection string needed
- If using SQL Server: Set `DATABASE_CONNECTION_STRING` in environment
- For production: Use external database service (Azure SQL, AWS RDS, etc.)

### CORS Issues

- Update `CORS_ALLOWED_ORIGINS` in environment variables
- Make sure frontend URLs are included
- Restart container after changing CORS settings

## Deployment to Cloud Platforms

### Azure Container Instances

```powershell
az container create \
  --resource-group myResourceGroup \
  --name kernalagent-backend \
  --image kernalagent-backend:latest \
  --dns-name-label kernalagent-backend \
  --ports 8080 \
  --environment-variables JWT_KEY="your-key" JWT_ISSUER="KernalAgentBackend"
```

### AWS ECS/Fargate

1. Push image to ECR
2. Create task definition with environment variables
3. Deploy to ECS cluster

### Google Cloud Run

```powershell
gcloud run deploy kernalagent-backend \
  --image gcr.io/PROJECT_ID/kernalagent-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars JWT_KEY="your-key"
```

## Multi-Stage Build Benefits

The Dockerfile uses multi-stage builds:
- **Stage 1 (build)**: Contains full SDK for building
- **Stage 2 (publish)**: Publishes the application
- **Stage 3 (final)**: Contains only runtime, smaller image size

This results in a smaller final image (~200MB vs ~1GB).

## Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Use secrets management** in production (Azure Key Vault, AWS Secrets Manager, etc.)
3. **Run as non-root user** - Dockerfile already does this
4. **Use strong JWT keys** - Generate random keys for production
5. **Keep images updated** - Regularly update base images
6. **Scan for vulnerabilities**:
   ```powershell
   docker scan kernalagent-backend:latest
   ```

## Next Steps

1. Set up CI/CD pipeline (GitHub Actions, Azure DevOps, etc.)
2. Configure production database
3. Set up monitoring and logging
4. Configure reverse proxy (nginx, Traefik, etc.)
5. Set up SSL/TLS certificates

