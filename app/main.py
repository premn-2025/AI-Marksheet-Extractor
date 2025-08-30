from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
import uvicorn
import logging
from datetime import datetime
import os

# Import custom modules
from app.services.extractor import MarksheetExtractor
from app.models.schemas import MarksheetResponse, ErrorResponse, BatchResponse
from app.utils.file_handler import FileHandler
from app.utils.validators import FileValidator
from app.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Marksheet Extraction API",
    description="""
    AI-powered API for extracting structured data from marksheet images and PDFs.
    
    ## Features
    * Support for JPG, PNG, PDF, and WebP files
    * LLM-powered extraction (Google Gemini via AI Studio)
    * Confidence scores for all extracted fields
    * Structured JSON output with consistent schema
    * Batch processing support
    * API key authentication (optional)
    * Beautiful web interface for testing
    
    ## Usage
    Upload a marksheet file and get structured JSON data with confidence scores.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (after CORS middleware)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Security
security = HTTPBearer(auto_error=False)

# Initialize services
file_handler = FileHandler()
file_validator = FileValidator()
extractor = MarksheetExtractor()

async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """Verify API key if authentication is enabled"""
    if not settings.enable_auth:  # FIX: Use new settings format
        return True

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="API key required. Use 'Bearer YOUR_API_KEY' in Authorization header"
        )

    try:
        file_validator.validate_api_key(credentials.credentials)
        return True
    except HTTPException:
        raise

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Internal server error occurred",
            error_code="INTERNAL_ERROR"
        ).model_dump()
    )

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def frontend():
    """Serve the frontend demo page"""
    try:
        file_path = os.path.join("static", "index.html")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        else:
            raise FileNotFoundError("Frontend file not found")
    except FileNotFoundError:
        return HTMLResponse(
            content="""
            <h1>Frontend Not Found</h1>
            <p>Please ensure static/index.html exists</p>
            <p><a href="/docs">Visit API Documentation</a></p>
            """,
            status_code=404
        )

@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    try:
        return {
            "status": "healthy",
            "services": {
                "api": "running",
                "llm": settings.llm_provider,  # FIX: Use new settings
                "file_handler": "ready"
            },
            "config": {
                "max_file_size": f"{settings.max_file_size / (1024*1024):.1f}MB",
                "allowed_extensions": list(settings.allowed_extensions),
                "auth_enabled": settings.enable_auth,
                "provider": settings.llm_provider
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/extract", response_model=MarksheetResponse, tags=["Extraction"])
async def extract_marksheet(
    file: UploadFile = File(..., description="Marksheet file (JPG, PNG, PDF, WebP) - Max 10MB"),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Extract structured data from marksheet image or PDF
    """
    try:
        logger.info(f"Processing extraction request for file: {file.filename}")

        # Validate file
        file_validator.validate_file(file)

        # Process file (returns file_type, base64_string)
        file_type, base64_content = await file_handler.process_upload(file)

        # Extract data using LLM
        logger.info(f"Starting LLM extraction for: {file.filename}")
        extracted_data = await extractor.extract_data(base64_content, file.filename)

        # Get extraction metadata
        metadata = extractor.get_extraction_metadata(file.filename)

        logger.info(f"Extraction completed successfully for: {file.filename}")

        return MarksheetResponse(
            success=True,
            message="Data extracted successfully",
            data=extracted_data,
            extraction_metadata=metadata,
            timestamp=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Extraction failed for {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )

@app.post("/extract/batch", response_model=BatchResponse, tags=["Batch Processing"])
async def extract_batch(
    files: List[UploadFile] = File(..., description="Multiple marksheet files (max 10)"),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Process multiple marksheet files in batch
    """
    try:
        # Validate batch size
        if len(files) > settings.max_batch_files:
            raise HTTPException(
                status_code=400,
                detail=f"Too many files. Maximum {settings.max_batch_files} files allowed per batch"
            )

        logger.info(f"Processing batch extraction for {len(files)} files")

        # Validate all files first
        file_validator.validate_batch_files(files)

        # Process all files
        batch_data = []
        for file in files:
            try:
                file_type, base64_content = await file_handler.process_upload(file)
                batch_data.append((base64_content, file.filename))
            except Exception as e:
                logger.error(f"Failed to process file {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Failed to process {file.filename}: {str(e)}"
                )

        # Extract data from all files
        results = await extractor.extract_batch_data(batch_data)

        # Convert to response format
        successful_results = []
        failed_files = []

        for result in results:
            if result["success"]:
                successful_results.append(MarksheetResponse(
                    success=True,
                    message="Data extracted successfully",
                    data=result["data"],
                    extraction_metadata=result.get("metadata", {}),
                    timestamp=datetime.utcnow()
                ))
            else:
                failed_files.append({
                    "filename": result["filename"],
                    "error": result["error"]
                })

        logger.info(f"Batch processing completed: {len(successful_results)} successful, {len(failed_files)} failed")

        return BatchResponse(
            success=True,
            results=successful_results,
            failed_files=failed_files,
            total_processed=len(files),
            successful_count=len(successful_results),
            failed_count=len(failed_files),
            timestamp=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )

@app.get("/info", tags=["Information"])
async def get_api_info():
    """Get API configuration and model information"""
    return {
        "api_version": "1.0.0",
        "llm_provider": settings.llm_provider,
        "supported_formats": list(settings.allowed_extensions),
        "max_file_size_mb": settings.max_file_size / (1024 * 1024),
        "max_batch_files": settings.max_batch_files,
        "authentication_enabled": settings.enable_auth,
        "features": {
            "single_extraction": True,
            "batch_processing": True,
            "confidence_scoring": True,
            "web_interface": True,
            "multiple_formats": True
        }
    }

# Add a simple redirect from /frontend to /
@app.get("/frontend", response_class=HTMLResponse, tags=["Frontend"])
async def frontend_redirect():
    """Redirect to main frontend"""
    return HTMLResponse(
        content='<script>window.location.href = "/";</script>',
        status_code=302
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
