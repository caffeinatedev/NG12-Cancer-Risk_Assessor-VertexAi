"""
Chat Engine for conversational clinical guideline queries.

This module provides session-managed chat functionality with context preservation
and grounding to NG12 guidelines through the RAG pipeline.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .models import ChatResponse, Message, Citation
from .rag_pipeline import RAGPipeline


class ChatEngine:
    """
    Conversational interface for clinical guideline queries with session management.
    
    Provides context-aware chat functionality that maintains conversation history
    and ensures all responses are grounded in NG12 guidelines.
    """
    
    def __init__(self, rag_pipeline: RAGPipeline):
        """
        Initialize the chat engine with a RAG pipeline.
        
        Args:
            rag_pipeline: Shared RAG pipeline for guideline retrieval
        """
        self.rag_pipeline = rag_pipeline
        self.sessions: Dict[str, List[Message]] = {}
    
    async def process_chat_message(
        self, 
        session_id: str, 
        message: str, 
        top_k: int = 5
    ) -> ChatResponse:
        """
        Process a chat message and generate a response with citations.
        
        Args:
            session_id: Unique session identifier
            message: User's chat message
            top_k: Number of relevant chunks to retrieve
            
        Returns:
            ChatResponse: AI response with citations and metadata
        """
        # Initialize session if it doesn't exist
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        # Add user message to session history
        user_message = Message(
            role="user",
            content=message,
            timestamp=datetime.utcnow()
        )
        self.sessions[session_id].append(user_message)
        
        # Build conversation context
        conversation_history = self._build_conversation_context(session_id)
        
        # Generate response using RAG pipeline
        response = await self.rag_pipeline.generate_chat_response(
            query=message,
            conversation_history=conversation_history,
            top_k=top_k
        )
        
        # Create assistant message
        assistant_message = Message(
            role="assistant",
            content=response.content,
            timestamp=datetime.utcnow(),
            citations=response.citations
        )
        
        # Add assistant message to session history
        self.sessions[session_id].append(assistant_message)
        
        return ChatResponse(
            session_id=session_id,
            answer=response.content,
            citations=response.citations,
            timestamp=assistant_message.timestamp
        )
    
    def get_session_history(self, session_id: str) -> List[Message]:
        """
        Retrieve conversation history for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            List[Message]: Complete conversation history
            
        Raises:
            KeyError: If session doesn't exist
        """
        if session_id not in self.sessions:
            raise KeyError(f"Session {session_id} not found")
        
        return self.sessions[session_id].copy()
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a chat session and clear its history.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            bool: True if session was deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def _build_conversation_context(self, session_id: str) -> str:
        """
        Build conversation context string from session history.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            str: Formatted conversation context
        """
        if session_id not in self.sessions or not self.sessions[session_id]:
            return ""
        
        context_parts = []
        for message in self.sessions[session_id][-10:]:  # Last 10 messages for context
            role_prefix = "User" if message.role == "user" else "Assistant"
            context_parts.append(f"{role_prefix}: {message.content}")
        
        return "\n".join(context_parts)
    
    def get_active_sessions(self) -> List[str]:
        """
        Get list of active session IDs.
        
        Returns:
            List[str]: List of active session identifiers
        """
        return list(self.sessions.keys())
    
    def get_session_count(self) -> int:
        """
        Get total number of active sessions.
        
        Returns:
            int: Number of active sessions
        """
        return len(self.sessions)