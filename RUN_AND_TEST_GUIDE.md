# How to Run and Test the Application

This guide will walk you through running the backend and testing it with the desktop app.

## Prerequisites

- .NET SDK (for backend)
- Node.js and npm (for frontend, optional)
- Visual Studio 2022 or VS Code (for desktop app)

## Step 1: Set Up Backend Environment

1. Navigate to the backend directory:
   ```powershell
   cd "Backend\KernalAgentBackend"
   ```

2. Create your `.env` file:
   ```powershell
   copy .env.example .env
   ```

3. Edit `.env` and set a JWT key (REQUIRED):
   ```
   JWT_KEY=YourSuperSecretKeyThatShouldBeAtLeast32CharactersLong!ChangeThisInProduction
   JWT_ISSUER=KernalAgentBackend
   JWT_AUDIENCE=KernalAgentFrontend
   DATABASE_CONNECTION_STRING=
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
   ```

   **Important:** Generate a secure random key. You can use PowerShell:
   ```powershell
   -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})
   ```

## Step 2: Run the Backend

1. Restore packages (first time only):
   ```powershell
   dotnet restore
   ```

2. Run the backend:
   ```powershell
   dotnet run
   ```

   The backend will start on:
   - HTTP: `http://localhost:5042`
   - HTTPS: `https://localhost:7062`
   - Swagger UI: `https://localhost:7062/swagger` (in development)

3. Verify it's running:
   - Open browser to `https://localhost:7062/swagger`
   - You should see the API documentation

## Step 3: Test Backend with Swagger (Optional)

1. Open Swagger UI: `https://localhost:7062/swagger`

2. Test Signup:
   - Find `POST /api/auth/signup`
   - Click "Try it out"
   - Enter test data:
     ```json
     {
       "name": "Test User",
       "email": "test@example.com",
       "password": "test123"
     }
     ```
   - Click "Execute"
   - You should get a response with a token

3. Test Login:
   - Find `POST /api/auth/login`
   - Click "Try it out"
   - Enter credentials:
     ```json
     {
       "email": "test@example.com",
       "password": "test123"
     }
     ```
   - Click "Execute"
   - You should get a token

4. Test Protected Endpoint:
   - Find `GET /api/dashboard/skills`
   - Click "Authorize" button at top
   - Enter: `Bearer YOUR_TOKEN_HERE` (copy token from login response)
   - Click "Authorize", then "Close"
   - Click "Try it out" and "Execute"
   - You should get skills data

## Step 4: Set Up Desktop App Environment

1. Navigate to desktop app directory:
   ```powershell
   cd "Desktop-App\Kernel Agent"
   ```

2. Create `.env` file (optional, has defaults):
   ```powershell
   copy .env.example .env
   ```

3. Edit `.env` if needed:
   ```
   API_BASE_URL=http://localhost:5042/api
   ```

   **Note:** The default should work if backend is on port 5042

## Step 5: Build and Run Desktop App

### Option A: Using Visual Studio

1. Open `Kernel Agent.slnx` in Visual Studio 2022
2. Set build configuration to "Debug"
3. Press F5 or click "Start"
4. The app will build and launch

### Option B: Using Command Line

1. Build the project:
   ```powershell
   dotnet build
   ```

2. Run the project:
   ```powershell
   dotnet run --project "Kernel Agent.csproj"
   ```

## Step 6: Test Desktop App with Backend

1. **First Launch:**
   - Desktop app will check for authentication
   - If not authenticated, a login dialog will appear

2. **Create Account (Signup):**
   - Click "Sign Up" button in the login dialog
   - Enter:
     - Name: `Test User`
     - Email: `test@example.com`
     - Password: `test123`
   - Click "Sign Up"
   - If successful, you'll be logged in

3. **Login:**
   - If you already have an account, enter:
     - Email: `test@example.com`
     - Password: `test123`
   - Click "Login"
   - If successful, you'll be logged in

4. **Verify Connection:**
   - After login, the app should be authenticated
   - You can navigate through the app
   - The app can now make authenticated API calls to the backend

## Troubleshooting

### Backend won't start

**Error: "JWT_KEY environment variable is required"**
- Solution: Make sure `.env` file exists in `Backend\KernalAgentBackend\`
- Verify `JWT_KEY` is set in the `.env` file

**Error: Port already in use**
- Solution: Change port in `Properties\launchSettings.json` or stop the process using the port

**Error: Certificate issues (HTTPS)**
- Solution: Trust the development certificate:
  ```powershell
  dotnet dev-certs https --trust
  ```

### Desktop app can't connect

**Error: Connection refused**
- Solution: Make sure backend is running on `http://localhost:5042`
- Check firewall settings
- Verify `API_BASE_URL` in desktop app `.env` matches backend URL

**Error: Login fails**
- Solution: 
  - Check backend is running
  - Verify backend logs for errors
  - Try creating account first via Swagger UI
  - Check network connectivity

**Error: .env file not found**
- Solution: Create `.env` file in `Desktop-App\Kernel Agent\` directory
- Or the app will use default `http://localhost:5042/api`

### Testing Tips

1. **Check Backend Logs:**
   - Backend logs will show incoming requests
   - Look for authentication attempts
   - Check for CORS errors

2. **Use Browser DevTools (if testing frontend):**
   - Open Network tab
   - Check API requests
   - Verify Authorization headers

3. **Test API Directly:**
   - Use Swagger UI for quick testing
   - Use Postman or curl for more control
   - Example curl command:
     ```powershell
     curl -X POST http://localhost:5042/api/auth/login -H "Content-Type: application/json" -d '{\"email\":\"test@example.com\",\"password\":\"test123\"}'
     ```

## Quick Test Checklist

- [ ] Backend `.env` file created with `JWT_KEY`
- [ ] Backend running on `http://localhost:5042`
- [ ] Swagger UI accessible at `https://localhost:7062/swagger`
- [ ] Can create account via Swagger
- [ ] Can login via Swagger
- [ ] Desktop app `.env` file created (optional)
- [ ] Desktop app builds successfully
- [ ] Desktop app shows login dialog on first launch
- [ ] Can create account via desktop app
- [ ] Can login via desktop app
- [ ] Desktop app successfully authenticates

## Next Steps

Once everything is working:
1. Test all desktop app features that require backend
2. Test frontend web app (if using)
3. Set up production environment variables
4. Configure database for production (if needed)

