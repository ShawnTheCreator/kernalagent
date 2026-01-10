# Testing Guide - Backend & Desktop App

## Quick Start (5 minutes)

### 1. Setup Backend Environment

Run the setup script:
```powershell
.\setup-backend.ps1
```

Or manually:
```powershell
cd Backend\KernalAgentBackend
copy .env.example .env
# Edit .env and set JWT_KEY (at least 32 characters)
```

### 2. Start Backend

```powershell
cd Backend\KernalAgentBackend
dotnet run
```

**Expected output:**
```
Now listening on: http://localhost:5042
Now listening on: https://localhost:7062
```

### 3. Test Backend (Optional)

Open browser: `https://localhost:7062/swagger`

Or run test script:
```powershell
.\test-backend.ps1
```

### 4. Setup Desktop App

```powershell
cd "Desktop-App\Kernel Agent"
# .env file is optional - defaults to http://localhost:5042/api
```

### 5. Run Desktop App

**Visual Studio:**
- Open `Kernel Agent.slnx`
- Press F5

**Command Line:**
```powershell
cd "Desktop-App\Kernel Agent"
dotnet run
```

### 6. Test Login Flow

1. Desktop app opens → Login dialog appears
2. Click "Sign Up"
3. Enter:
   - Name: `Test User`
   - Email: `test@example.com`
   - Password: `test123`
4. Click "Sign Up"
5. ✅ Successfully logged in!

## Testing Scenarios

### Scenario 1: New User Signup
1. Open desktop app
2. Click "Sign Up" in login dialog
3. Fill in form and submit
4. **Expected:** Login successful, dialog closes

### Scenario 2: Existing User Login
1. Open desktop app
2. Enter credentials from previous signup
3. Click "Login"
4. **Expected:** Login successful, dialog closes

### Scenario 3: Invalid Credentials
1. Open desktop app
2. Enter wrong email/password
3. Click "Login"
4. **Expected:** Error message shown

### Scenario 4: Backend Offline
1. Stop backend server
2. Try to login in desktop app
3. **Expected:** Connection error or timeout

## Verification Checklist

- [ ] Backend starts without errors
- [ ] Swagger UI accessible
- [ ] Can create account via Swagger
- [ ] Can login via Swagger
- [ ] Desktop app builds successfully
- [ ] Desktop app shows login dialog
- [ ] Can create account via desktop app
- [ ] Can login via desktop app
- [ ] Token is stored after login
- [ ] App remembers login on restart

## Debugging Tips

### Check Backend Logs
Backend console shows:
- Incoming requests
- Authentication attempts
- Errors

### Check Desktop App
- Look for error dialogs
- Check Windows Event Viewer for crashes
- Use Visual Studio debugger

### Network Issues
- Verify backend is on `http://localhost:5042`
- Check firewall settings
- Try `curl http://localhost:5042/api/auth/login` from PowerShell

### Common Errors

**"JWT_KEY environment variable is required"**
→ Create `.env` file in backend directory

**"Connection refused"**
→ Backend not running or wrong port

**"Invalid email or password"**
→ Check credentials or create new account

## API Testing with curl

### Signup
```powershell
curl -X POST http://localhost:5042/api/auth/signup `
  -H "Content-Type: application/json" `
  -d '{\"name\":\"Test User\",\"email\":\"test@example.com\",\"password\":\"test123\"}'
```

### Login
```powershell
curl -X POST http://localhost:5042/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"test@example.com\",\"password\":\"test123\"}'
```

### Get Skills (requires token)
```powershell
curl -X GET http://localhost:5042/api/dashboard/skills `
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Next Steps

Once basic testing works:
1. Test all desktop app features
2. Test frontend web app (if using)
3. Test error handling
4. Test edge cases
5. Performance testing

