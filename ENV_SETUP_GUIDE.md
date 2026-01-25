# Environment Variables Setup Guide

This guide explains how to set up `.env` files for secure configuration across all three applications.

## Overview

All sensitive configuration (API keys, JWT secrets, database connection strings, etc.) should be stored in `.env` files, which are **never committed to version control**.

## Backend (C# .NET)

### Setup

1. Navigate to `Backend/KernalAgentBackend/`
2. Copy the example file:
   ```bash
   copy .env.example .env
   ```
3. Edit `.env` and fill in your values

### Required Variables

- **JWT_KEY** (REQUIRED): A secure random string (at least 32 characters) for JWT token signing
- **JWT_ISSUER**: The issuer name for JWT tokens (default: KernalAgentBackend)
- **JWT_AUDIENCE**: The audience for JWT tokens (default: KernalAgentFrontend)
- **DATABASE_CONNECTION_STRING**: SQL Server connection string (leave empty for InMemory DB in development)
- **CORS_ALLOWED_ORIGINS**: Comma-separated list of allowed frontend origins

### Example `.env` file

```
JWT_KEY=YourSuperSecretKeyThatShouldBeAtLeast32CharactersLong!ChangeThisInProduction
JWT_ISSUER=KernalAgentBackend
JWT_AUDIENCE=KernalAgentFrontend
DATABASE_CONNECTION_STRING=
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Notes

- The backend uses `DotNetEnv` package to load `.env` files
- JWT_KEY is **required** - the app will not start without it
- For production, use a strong, randomly generated JWT key

## Frontend (Next.js)

### Setup

1. Navigate to `Frontend/`
2. Copy the example file:
   ```bash
   copy .env.example .env.local
   ```
3. Edit `.env.local` and configure your values

### Required Variables

- **NEXT_PUBLIC_API_URL**: The backend API base URL (default: http://localhost:5042/api)
- **NEXT_PUBLIC_WS_URL**: WebSocket URL for real-time updates (default: ws://localhost:8000/ws/stream)

### Example `.env.local` file

```
NEXT_PUBLIC_API_URL=http://localhost:5042/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/stream
```

### Notes

- Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser
- Restart the Next.js dev server after changing environment variables
- `.env.local` is automatically ignored by git

## Desktop App (WinUI)

### Setup

1. Navigate to `Desktop-App/Kernel Agent/`
2. Copy the example file:
   ```bash
   copy .env.example .env
   ```
3. Edit `.env` and configure your values

### Required Variables

- **API_BASE_URL**: The backend API base URL (default: http://localhost:5042/api)
- **GOOGLE_APPLICATION_CREDENTIALS**: Path to Google Cloud service account key (if using Google Speech API)

### Example `.env` file

```
API_BASE_URL=http://localhost:5042/api
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
```

### Notes

- The desktop app uses `dotenv.net` package to load `.env` files
- Place the `.env` file in the same directory as the executable
- The `.env` file is already in `.gitignore`

## Security Best Practices

1. **Never commit `.env` files** - They are already in `.gitignore`
2. **Use strong, unique values** for JWT keys in production
3. **Rotate secrets periodically** for enhanced security
4. **Use different values** for development and production environments
5. **Keep `.env` files secure** - Only share with team members who need access

## Generating a Secure JWT Key

You can generate a secure JWT key using:

**PowerShell:**
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})
```

**Online:**
- Use a secure random string generator
- Ensure it's at least 32 characters long
- Include a mix of letters, numbers, and special characters

## Troubleshooting

### Backend won't start
- Ensure `.env` file exists in `Backend/KernalAgentBackend/`
- Verify `JWT_KEY` is set and is at least 32 characters
- Check that the `.env` file is in the correct location

### Frontend can't connect to backend
- Verify `NEXT_PUBLIC_API_URL` in `.env.local` matches your backend URL
- Restart the Next.js dev server after changing `.env.local`
- Check CORS settings in backend `.env` file

### Desktop app can't connect
- Ensure `.env` file exists in the app directory
- Verify `API_BASE_URL` is correct
- Check that `dotenv.net` package is installed

