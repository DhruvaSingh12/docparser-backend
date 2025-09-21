### Method 1: Single Command 

# Navigate to project and start server in one go
cd F:\Projects\docparse\backend; .\.venv\Scripts\Activate.ps1; F:/Projects/docparse/backend/.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000


### Method 2: Step by Step
```powershell
# 1. Navigate to your project
cd F:\Projects\docparse\backend

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Start the server
python -m uvicorn app.main:app --reload --port 8000
```

## 📋 Startup Checklist

### Before Starting (First Time Each Day):
```powershell
# Check if virtual environment is active (should show (.venv) in prompt)
python -c "import sys; print('✅ Using:', sys.executable)"

# Optional: Check database connection
python -c "from app.db import engine; engine.connect(); print('✅ Database connected')"
```

### Your Server URLs:
- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/health
- **Root**: http://127.0.0.1:8000/

## 🛠️ Development Commands

### Start Development Server:
```powershell
# With auto-reload (for development)
python -m uvicorn app.main:app --reload --port 8000

# Production mode (no auto-reload)
python -m uvicorn app.main:app --port 8000

# With host binding (to access from other devices)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Commands:
```powershell
# Initialize database (only needed once or after schema changes)
python init_db.py

# Setup Row Level Security (only needed once)
python setup_rls.py

# Test database connection
python test_setup.py
```

### Package Management:
```powershell
# Install all dependencies
pip install -r requirements.txt

# Add new package and update requirements
pip install package_name
pip freeze > requirements.txt
```

## 📝 Create Startup Script (Optional)

Save this as `start.bat` in your project folder:
```batch
@echo off
cd /d F:\Projects\docparse\backend
call .venv\Scripts\activate.bat
echo ✅ Virtual environment activated
echo 🚀 Starting DocParse API server...
python -m uvicorn app.main:app --reload --port 8000
pause
```

Then just double-click `start.bat` to start your project!

## 🐍 PowerShell Profile (Advanced)

Add this to your PowerShell profile for quick access:
```powershell
# Add to $PROFILE (run: notepad $PROFILE)
function Start-DocParse {
    Set-Location "F:\Projects\docparse\backend"
    .\.venv\Scripts\Activate.ps1
    python -m uvicorn app.main:app --reload --port 8000
}

# Usage: Just type "Start-DocParse" in any PowerShell window
```

## 🔧 Troubleshooting

### If Virtual Environment Won't Activate:
```powershell
# Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate
.\.venv\Scripts\Activate.ps1
```

### If Python Command Not Found:
```powershell
# Use full path
F:/Projects/docparse/backend/.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

### If Port 8000 is Busy:
```powershell
# Use different port
python -m uvicorn app.main:app --reload --port 8001
```

## 📱 Mobile Development URLs

When your React Native app connects to the API:
```
# If testing on physical device (same network)
http://YOUR_COMPUTER_IP:8000

# If using Android emulator
http://10.0.2.2:8000

# If using iOS simulator
http://127.0.0.1:8000
```

## ⚡ Quick Commands Summary

```powershell
# Daily startup
cd F:\Projects\docparse\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000

# Open API docs
start http://127.0.0.1:8000/docs

# Stop server: Ctrl+C in terminal
```

**Pro Tip**: Bookmark http://127.0.0.1:8000/docs in your browser for quick API testing!