# Environment Variables Setup

This frontend application uses `.env.local` files for configuration.

## Setup Instructions

1. Copy the example file:
   ```bash
   cp .env.example .env.local
   ```

2. Edit `.env.local` and configure:
   - **NEXT_PUBLIC_API_URL**: The backend API base URL (default: http://localhost:5042/api)
   - **NEXT_PUBLIC_WS_URL**: WebSocket URL for real-time updates (default: ws://localhost:8000/ws/stream)

## Important Notes

- **Never commit `.env.local` files to version control**
- The `.env.local` file is already in `.gitignore`
- Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser
- Restart the Next.js dev server after changing environment variables

## Example .env.local file

```
NEXT_PUBLIC_API_URL=http://localhost:5042/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/stream
```

