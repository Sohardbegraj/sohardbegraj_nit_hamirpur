from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Import extractor
from app.extractor import OllamaBillExtractor

app = FastAPI(
    title="Bill Extraction API - HackRx Datathon",
    description="Extract line items from medical bills",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2-vision:11b")

# Initialize extractor
extractor = OllamaBillExtractor(ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)


# Request model
class BillExtractionRequest(BaseModel):
    document: str  # URL to the document


@app.on_event("startup")
async def startup_event():
    """Test Ollama connection on startup"""
    print(f"\n{'='*60}")
    print(f"🚀 Starting Bill Extraction API - HackRx Datathon")
    print(f"{'='*60}")
    print(f"📡 Ollama Server: {OLLAMA_URL}")
    print(f"🤖 Model: {OLLAMA_MODEL}")
    
    if extractor.test_connection():
        print("✅ Ollama connection successful!")
    else:
        print("⚠️  Warning: Cannot connect to Ollama server")
    
    print(f"{'='*60}\n")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Bill Extraction API - HackRx Datathon",
        "status": "running",
        "model": OLLAMA_MODEL,
        "endpoints": {
            "extract": "POST /extract-bill-data"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    ollama_status = extractor.test_connection()
    
    return {
        "status": "healthy" if ollama_status else "degraded",
        "ollama_connected": ollama_status,
        "model": OLLAMA_MODEL
    }


@app.post("/extract-bill-data")
async def extract_bill_data(request: BillExtractionRequest):
    """
    Extract bill data from document URL
    
    Request Body:
    {
        "document": "https://example.com/bill.pdf"
    }
    
    Response:
    {
        "is_success": true,
        "token_usage": {
            "total_tokens": 1500,
            "input_tokens": 1000,
            "output_tokens": 500
        },
        "data": {
            "pagewise_line_items": [
                {
                    "page_no": "1",
                    "page_type": "Bill Detail",
                    "bill_items": [
                        {
                            "item_name": "Consultation Fee",
                            "item_amount": 500.0,
                            "item_rate": 500.0,
                            "item_quantity": 1.0
                        }
                    ]
                }
            ],
            "total_item_count": 1
        }
    }
    """
    
    start_time = time.time()
    
    try:
        # Validate document URL
        if not request.document:
            raise HTTPException(status_code=400, detail="Document URL is required")
        
        if not request.document.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid document URL")
        
        print(f"\n📥 Received extraction request")
        print(f"   URL: {request.document[:100]}...")
        
        # Extract bill data
        result = extractor.extract_bill_data(request.document)
        
        # Add processing time for logging
        processing_time = time.time() - start_time
        print(f"⏱️  Processing time: {processing_time:.2f}s")
        
        # Return result
        return JSONResponse(
            content=result,
            status_code=200 if result["is_success"] else 500
        )
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        
        # Return error response in HackRx format
        return JSONResponse(
            content={
                "is_success": False,
                "token_usage": {
                    "total_tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0
                },
                "data": {
                    "pagewise_line_items": [],
                    "total_item_count": 0
                },
                "error": str(e)
            },
            status_code=500
        )


if __name__ == "__main__":
    # Get port from environment
    port = int(os.getenv("PORT", 8000))
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║        Bill Extraction API - HackRx Datathon                 ║
╚══════════════════════════════════════════════════════════════╝

🌐 Server: http://0.0.0.0:{port}
📡 Ollama: {OLLAMA_URL}
🤖 Model: {OLLAMA_MODEL}

Endpoints:
  GET  /                - API info
  GET  /health          - Health check
  POST /extract-bill-data - Extract bill data

Press Ctrl+C to stop
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=port)