@echo off
echo ========================================
echo Testing Bill Extraction API - HackRx Format
echo ========================================
echo.

REM Test 1: Health Check
echo [1/3] Testing health endpoint...
curl -s http://localhost:8000/health
echo.
echo.

REM Test 2: Root endpoint
echo [2/3] Testing root endpoint...
curl -s http://localhost:8000/
echo.
echo.

REM Test 3: Extract bill data with sample URL
echo [3/3] Testing extraction with sample URL...
echo.
echo Note: Using a sample URL - replace with actual training data URL
echo.

REM Create JSON payload
echo {"document": "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png"} > temp_request.json

REM Send request
curl -X POST "http://localhost:8000/extract-bill-data" ^
  -H "Content-Type: application/json" ^
  -d @temp_request.json ^
  -o temp_response.json

echo.
echo Response saved to temp_response.json
echo.

REM Display response
type temp_response.json

REM Cleanup
del temp_request.json

echo.
echo.
echo ========================================
echo Testing complete!
echo ========================================
echo.
echo To test with training data:
echo 1. Download training samples
echo 2. Upload to accessible URL
echo 3. Update URL in this script
echo.
pause