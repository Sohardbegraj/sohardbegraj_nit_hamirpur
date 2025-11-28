@echo off
echo Starting Bill Extraction API Server
echo.
call venv\Scripts\activate.bat
echo Starting server on http://localhost:8000
echo Press Ctrl+C to stop
echo.
python app/main.py