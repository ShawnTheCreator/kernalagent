# Quick Docker Commands

## Build and Run

```powershell
# Development
docker-compose up --build

# Production
docker-compose -f docker-compose.prod.yml up -d --build
```

## Common Commands

```powershell
# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild
docker-compose up --build --force-recreate
```

## Environment Setup

Create `.env` file with:
```
JWT_KEY=YourSuperSecretKeyThatShouldBeAtLeast32CharactersLong!
JWT_ISSUER=KernalAgentBackend
JWT_AUDIENCE=KernalAgentFrontend
DATABASE_CONNECTION_STRING=
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

See `DOCKER_DEPLOY.md` for full documentation.

