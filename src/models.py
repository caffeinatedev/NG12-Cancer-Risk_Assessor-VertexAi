"""
Data models for the NG12 Cancer Risk Assessor.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class PatientRecord(BaseModel):
    """Patient data model matching the requirements."""
    patient_id: str
    name: str
    age: int
    gender: str
    smoking_history: str
    symptoms: List[str]
    symptom_duration_days: int


class DocumentMetadata(BaseModel):
    """Metadata for document chunks in the vector store."""
    chunk_id: str = Field(description="Unique identifier (e.g., 'ng12_0023_01')")
    page_number: int = Field(description="PDF page number")
    section_title: str = Field(description="NG12 section heading")
    excerpt: str = Field(description="Text content for citations")
    document_source: str = Field(default="NG12 PDF", description="Source document")


class Citation(BaseModel):
    """Citation model for referencing NG12 guidelines."""
    source: str = Field(default="NG12 PDF")
    page: int
    chunk_id: str
    excerpt: str
    relevance_score: float


class AssessmentRequest(BaseModel):
    """Request model for patient assessment."""
    patient_id: str


class AssessmentResponse(BaseModel):
    """Response model for patient assessment."""
    patient_id: str
    assessment: str = Field(description="Urgent Referral | Urgent Investigation | No Action")
    reasoning: str
    citations: List[Citation]
    confidence_score: Optional[float] = None


class ChatRequest(BaseModel):
    """Request model for chat messages."""
    session_id: str
    message: str
    top_k: int = Field(default=5, description="Number of relevant chunks to retrieve")


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    session_id: str
    answer: str
    citations: List[Citation]
    timestamp: datetime


class Message(BaseModel):
    """Message model for chat history."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    role: str = Field(description="user | assistant")
    content: str
    timestamp: datetime
    citations: Optional[List[Citation]] = None


class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    session_id: str
    messages: List[Message]


class StatusResponse(BaseModel):
    """Generic status response."""
    success: bool
    message: str


class HealthResponse(BaseModel):
    """Health check response."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    status: str
    timestamp: datetime
    version: str = "1.0.0"


class RetrievedChunk(BaseModel):
    """Model for chunks retrieved from vector store."""
    chunk_id: str
    content: str
    metadata: DocumentMetadata
    similarity_score: float


class GeneratedResponse(BaseModel):
    """Model for generated responses from LLM."""
    content: str
    citations: List[Citation]
    model_metadata: Dict[str, Any]


class TextChunk(BaseModel):
    """Model for text chunks extracted from PDF."""
    chunk_id: str
    content: str
    page_number: int
    section_title: str
    start_char: int
    end_char: int


class ErrorResponse(BaseModel):
    """Error response model."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: str
    retry_after: Optional[int] = None