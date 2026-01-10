# Environment Variables Setup

This desktop application uses `.env` files for configuration.

## Setup Instructions

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure:
   - **API_BASE_URL**: The backend API base URL (default: http://localhost:5042/api)
   - **GOOGLE_APPLICATION_CREDENTIALS**: Path to Google Cloud service account key (if using Google Speech API)

## Important Notes

- **Never commit `.env` files to version control**
- The `.env` file is already in `.gitignore`
- The app uses `dotenv.net` package to load environment variables
- Place the `.env` file in the same directory as the executable

## Example .env file

```
API_BASE_URL=http://localhost:5042/api
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
```

