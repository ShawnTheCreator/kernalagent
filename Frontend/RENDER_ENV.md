# Frontend Environment Variables for Render

## Set these in your Render dashboard for the frontend service:

### API URLs (REQUIRED)
NEXT_PUBLIC_API_URL=https://kernalagent-backend.onrender.com/api
NEXT_PUBLIC_WS_URL=wss://kernalagent-microservice.onrender.com/ws/stream

### Firebase Configuration (if using Firebase Auth)
# Get these from your Firebase Console > Project Settings > General
NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id

### Node Environment
NODE_ENV=production

## Notes:
- Replace the URLs with your actual Render service URLs after deployment
- All NEXT_PUBLIC_* variables are exposed to the browser
- Never put sensitive keys in NEXT_PUBLIC_* variables
