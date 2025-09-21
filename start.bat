@echo off
cd /d F:\Projects\docparse\backend
call .venv\Scripts\activate.bat
echo Virtual environment activated
echo Starting DocParse API server...
python -m uvicorn app.main:app --reload --port 8000
pause