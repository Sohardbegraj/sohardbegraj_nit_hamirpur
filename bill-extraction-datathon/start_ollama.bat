@echo off
echo Starting Ollama server...
echo.
echo Ollama will listen on: http://0.0.0.0:11434
echo Press Ctrl+C to stop
echo.
set OLLAMA_HOST=0.0.0.0:11434
ollama serve