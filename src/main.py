"""
FastAPI application for the NG12 Cancer Risk Assessor.

This module provides the main API endpoints for patient assessment and chat functionality,
with proper error handling, CORS configuration, and static file serving.
"""
import os
import uuid
import logging
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
from dotenv import load_dotenv

from .models import (
    AssessmentRequest, AssessmentResponse, ChatRequest, ChatResponse,
    ChatHistoryResponse, StatusResponse, HealthResponse, ErrorResponse
)
from .assessment_engine import AssessmentEngine, AssessmentEngineError
from .chat_engine import ChatEngine
from .rag_pipeline import RAGPipeline
from .vector_store import VectorStore
from .embedding_service import EmbeddingService
from .patient_loader import PatientLoader, PatientNotFoundError, PatientNotFoundError
from .gemini_agent import GeminiAgent

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Global variables for shared components
rag_pipeline: Optional[RAGPipeline] = None
assessment_engine: Optional[AssessmentEngine] = None
chat_engine: Optional[ChatEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for initializing shared components.
    """
    global rag_pipeline, assessment_engine, chat_engine
    
    try:
        # Initialize core components
        print("Initializing NG12 Cancer Risk Assessor...")
        
        # Setup credentials file from environment variable if present
        # This resolves "seekable bit stream" errors by ensuring libraries see a file path
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            try:
                cred_path = "/tmp/google_credentials.json"
                with open(cred_path, "w") as f:
                    f.write(service_account_json)
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
                print(f"✓ Created temporary credentials file at {cred_path}")
            except Exception as e:
                print(f"⚠ Failed to create credentials file: {e}")

        # Initialize embedding service
        embedding_service = EmbeddingService(
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        )
        
        # Initialize vector store
        vector_store = VectorStore(
            store_path=os.getenv("VECTOR_STORE_PATH", "./data/vector_store")
        )
        
        # Initialize Gemini agent
        gemini_agent = GeminiAgent(
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            model_name=os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash")
        )
        
        # Initialize RAG pipeline (shared by both engines)
        rag_pipeline = RAGPipeline(
            vector_store=vector_store,
            embedding_service=embedding_service,
            gemini_agent=gemini_agent
        )
        
        # Initialize patient loader
        patient_loader = PatientLoader(
            data_file_path=os.getenv("PATIENT_DATA_PATH", "./data/patients.json")
        )
        
        # Initialize assessment engine
        assessment_engine = AssessmentEngine(
            rag_pipeline=rag_pipeline,
            patient_loader=patient_loader,
            gemini_agent=gemini_agent
        )
        
        # Initialize chat engine
        chat_engine = ChatEngine(rag_pipeline=rag_pipeline)
        
        print("✓ All components initialized successfully")
        
        yield
        
    except Exception as e:
        print(f"✗ Failed to initialize components: {e}")
        raise
    finally:
        # Cleanup resources
        print("Shutting down NG12 Cancer Risk Assessor...")


# Create FastAPI application
app = FastAPI(
    title="NG12 Cancer Risk Assessor",
    description="Clinical reasoning agent for cancer risk assessment using NICE NG12 guidelines",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),  # Convert to string!
            "request_id": str(uuid.uuid4())
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with structured error responses."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": {"exception_type": type(exc).__name__},
            "timestamp": datetime.utcnow().isoformat(),  # Convert to string!
            "request_id": str(uuid.uuid4())
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring service availability.
    
    Returns:
        HealthResponse: Service health status and metadata
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


# Test endpoint for debugging patient not found
@app.post("/test-patient-error")
async def test_patient_error():
    """Test endpoint to debug patient not found error."""
    try:
        patient = await assessment_engine.patient_loader.get_patient_by_id_async("INVALID-ID")
        return {"found": True}
    except PatientNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient not found (direct test): {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Other error: {type(e).__name__}: {str(e)}"
        )


# Patient assessment endpoint
@app.post("/assess")
async def assess_patient(request: AssessmentRequest):
    """
    Assess cancer risk for a patient based on their symptoms and NG12 guidelines.
    
    Args:
        request: Assessment request containing patient ID
        
    Returns:
        AssessmentResponse: Risk assessment with reasoning and citations
        
    Raises:
        HTTPException: If patient not found or assessment fails
    """
    if not assessment_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assessment engine not initialized"
        )
    
    try:
        result = await assessment_engine.assess_patient_risk(request.patient_id)
        return result
    except PatientNotFoundError:  # Catch specific exception
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient not found: {request.patient_id}"
        )
    except AssessmentEngineError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assessment failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during assessment: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


# Batch assessment endpoint
@app.post("/assess/batch")
async def assess_multiple_patients(patient_ids: List[str]):
    """
    Assess multiple patients in batch.
    
    Args:
        patient_ids: List of patient IDs to assess
        
    Returns:
        List of assessment responses
        
    Raises:
        HTTPException: If assessment engine not available
    """
    if not assessment_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assessment engine not initialized"
        )
    
    if not patient_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient IDs list cannot be empty"
        )
    
    try:
        results = await assessment_engine.assess_multiple_patients(patient_ids)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch assessment failed: {str(e)}"
        )


# Assessment statistics endpoint
@app.get("/assess/stats")
async def get_assessment_stats():
    """
    Get assessment engine statistics and health information.
    
    Returns:
        Dictionary with engine statistics
        
    Raises:
        HTTPException: If assessment engine not available
    """
    if not assessment_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assessment engine not initialized"
        )
    
    try:
        stats = assessment_engine.get_engine_stats()
        health = await assessment_engine.health_check()
        
        return {
            "engine_stats": stats,
            "health_status": health,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assessment stats: {str(e)}"
        )


# Chat message endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """
    Process a chat message about NG12 guidelines.
    
    Args:
        request: Chat request with session ID and message
        
    Returns:
        ChatResponse: AI response with citations
        
    Raises:
        HTTPException: If chat processing fails
    """
    if not chat_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat engine not initialized"
        )
    
    try:
        response = await chat_engine.process_chat_message(
            session_id=request.session_id,
            message=request.message,
            top_k=request.top_k
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        )


# Chat history endpoint
@app.get("/chat/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    """
    Retrieve conversation history for a chat session.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        ChatHistoryResponse: Complete conversation history
        
    Raises:
        HTTPException: If session not found
    """
    if not chat_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat engine not initialized"
        )
    
    try:
        messages = chat_engine.get_session_history(session_id)
        return ChatHistoryResponse(
            session_id=session_id,
            messages=messages
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )


# Delete chat session endpoint
@app.delete("/chat/{session_id}", response_model=StatusResponse)
async def delete_chat_session(session_id: str):
    """
    Delete a chat session and clear its history.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        StatusResponse: Deletion status
    """
    if not chat_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat engine not initialized"
        )
    
    success = chat_engine.delete_session(session_id)
    
    if success:
        return StatusResponse(
            success=True,
            message=f"Session {session_id} deleted successfully"
        )
    else:
        return StatusResponse(
            success=False,
            message=f"Session {session_id} not found"
        )


# Mount static files for frontend (if frontend directory exists)
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
    
    @app.get("/")
    async def serve_frontend():
        """Serve the main frontend page."""
        from fastapi.responses import FileResponse
        return FileResponse("frontend/index.html")


if __name__ == "__main__":
    # Development server configuration
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )