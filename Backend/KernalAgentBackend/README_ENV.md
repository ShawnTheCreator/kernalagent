# Environment Variables Setup

This backend application uses `.env` files for secure configuration management.

## Setup Instructions

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your values:
   - **JWT_KEY**: A secure random string (at least 32 characters) for JWT token signing
   - **JWT_ISSUER**: The issuer name for JWT tokens (default: KernalAgentBackend)
   - **JWT_AUDIENCE**: The audience for JWT tokens (default: KernalAgentFrontend)
   - **DATABASE_CONNECTION_STRING**: SQL Server connection string (leave empty for InMemory DB)
   - **CORS_ALLOWED_ORIGINS**: Comma-separated list of allowed frontend origins

## Important Security Notes

- **Never commit `.env` files to version control**
- The `.env` file is already in `.gitignore`
- Use strong, unique values for `JWT_KEY` in production
- Rotate `JWT_KEY` periodically for enhanced security

## Example .env file

```
JWT_KEY=YourSuperSecretKeyThatShouldBeAtLeast32CharactersLong!ChangeThisInProduction
JWT_ISSUER=KernalAgentBackend
JWT_AUDIENCE=KernalAgentFrontend
DATABASE_CONNECTION_STRING=
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

