# 1. Navigate to your project
cd F:\Projects\docparse\backend

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Start the server
python -m uvicorn app.main:app --reload --port 8000