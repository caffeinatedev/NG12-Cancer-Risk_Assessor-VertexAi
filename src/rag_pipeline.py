"""
RAG (Retrieval-Augmented Generation) pipeline for the NG12 Cancer Risk Assessor.
Orchestrates the retrieval of relevant NG12 guideline content and citation formatting.
"""
import logging
from typing import List, Optional, Dict, Any
import asyncio

from .models import RetrievedChunk, DocumentMetadata, Citation, TextChunk, GeneratedResponse
from .embedding_service import EmbeddingService, EmbeddingServiceError
from .vector_store import VectorStore, VectorStoreError, SearchResult
from .gemini_agent import GeminiAgent


logger = logging.getLogger(__name__)


class RAGPipelineError(Exception):
    """Custom exception for RAG pipeline errors."""
    pass


class RAGPipeline:
    """
    Core RAG pipeline that combines embedding generation and vector search.
    
    Provides unified interface for retrieving relevant NG12 guideline content
    with proper citation metadata for both assessment and chat functionalities.
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        gemini_agent: Optional[GeminiAgent] = None,
        default_top_k: int = 5,
        similarity_threshold: float = 0.001
    ):
        """
        Initialize the RAG pipeline.
        
        Args:
            embedding_service: Service for generating embeddings
            vector_store: Vector store for similarity search
            gemini_agent: Optional Gemini agent for response generation
            default_top_k: Default number of chunks to retrieve
            similarity_threshold: Minimum similarity score for results
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.gemini_agent = gemini_agent
        self.default_top_k = default_top_k
        self.similarity_threshold = similarity_threshold
        
        logger.info("Initialized RAG pipeline")
    
    async def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks for a given query.
        
        Args:
            query: Search query text
            top_k: Number of chunks to retrieve (defaults to pipeline default)
            filter_metadata: Optional metadata filters for search
            
        Returns:
            List of RetrievedChunk objects ranked by relevance
            
        Raises:
            RAGPipelineError: If retrieval fails
        """
        if not query or not query.strip():
            raise RAGPipelineError("Query cannot be empty")
        
        k = top_k or self.default_top_k
        
        try:
            # Generate query embedding
            logger.debug(f"Generating embedding for query: {query[:100]}...")
            query_embedding = await self.embedding_service.generate_query_embedding(query.strip())
            
            # Perform similarity search
            logger.debug(f"Searching for {k} most relevant chunks")
            search_results = await self.vector_store.similarity_search(
                query_embedding=query_embedding,
                top_k=k,
                filter_metadata=filter_metadata
            )
            
            # Filter by similarity threshold and convert to RetrievedChunk
            retrieved_chunks = []
            for result in search_results:
                if result.similarity_score >= self.similarity_threshold:
                    retrieved_chunk = RetrievedChunk(
                        chunk_id=result.chunk_id,
                        content=result.content,
                        metadata=result.metadata,
                        similarity_score=result.similarity_score
                    )
                    retrieved_chunks.append(retrieved_chunk)
            
            logger.info(f"Retrieved {len(retrieved_chunks)} relevant chunks for query")
            return retrieved_chunks
            
        except (EmbeddingServiceError, VectorStoreError) as e:
            raise RAGPipelineError(f"Failed to retrieve relevant chunks: {e}")
        except Exception as e:
            raise RAGPipelineError(f"Unexpected error during retrieval: {e}")
    
    def format_citations(self, chunks: List[RetrievedChunk]) -> List[Citation]:
        """
        Format retrieved chunks as citations.
        
        Args:
            chunks: List of retrieved chunks
            
        Returns:
            List of Citation objects with proper formatting
        """
        citations = []
        
        for chunk in chunks:
            citation = Citation(
                source="NG12 PDF",
                page=chunk.metadata.page_number,
                chunk_id=chunk.chunk_id,
                excerpt=chunk.metadata.excerpt,
                relevance_score=chunk.similarity_score
            )
            citations.append(citation)
        
        # Sort citations by relevance score (highest first)
        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        
        return citations
    
    def format_context_for_llm(
        self,
        chunks: List[RetrievedChunk],
        include_metadata: bool = True
    ) -> str:
        """
        Format retrieved chunks as context for LLM input.
        
        Args:
            chunks: List of retrieved chunks
            include_metadata: Whether to include metadata in context
            
        Returns:
            Formatted context string for LLM
        """
        if not chunks:
            return "No relevant information found in NG12 guidelines."
        
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            if include_metadata:
                header = f"[Source {i}: NG12 PDF, Page {chunk.metadata.page_number}, Section: {chunk.metadata.section_title}]"
                context_parts.append(header)
            
            context_parts.append(chunk.content)
            context_parts.append("")  # Empty line for separation
        
        return "\n".join(context_parts)
    
    async def search_and_format(
        self,
        query: str,
        top_k: Optional[int] = None,
        format_for_llm: bool = True,
        include_citations: bool = True
    ) -> Dict[str, Any]:
        """
        Perform search and return formatted results.
        
        Args:
            query: Search query
            top_k: Number of results to retrieve
            format_for_llm: Whether to format context for LLM
            include_citations: Whether to include citation objects
            
        Returns:
            Dictionary with formatted results
        """
        try:
            # Retrieve relevant chunks
            chunks = await self.retrieve_relevant_chunks(query, top_k)
            
            result = {
                "query": query,
                "num_results": len(chunks),
                "chunks": chunks
            }
            
            if format_for_llm:
                result["context"] = self.format_context_for_llm(chunks)
            
            if include_citations:
                result["citations"] = self.format_citations(chunks)
            
            return result
            
        except RAGPipelineError:
            raise
        except Exception as e:
            raise RAGPipelineError(f"Failed to search and format results: {e}")
    
    async def build_clinical_context(
        self,
        patient_symptoms: List[str],
        patient_demographics: Optional[Dict[str, Any]] = None,
        top_k: int = 8
    ) -> Dict[str, Any]:
        """
        Build clinical context for patient assessment.
        
        Args:
            patient_symptoms: List of patient symptoms
            patient_demographics: Optional patient demographic info
            top_k: Number of guideline chunks to retrieve
            
        Returns:
            Dictionary with clinical context and citations
        """
        if not patient_symptoms:
            raise RAGPipelineError("Patient symptoms cannot be empty")
        
        try:
            # Construct clinical query
            symptoms_text = ", ".join(patient_symptoms)
            
            # Add demographic context if available
            demographic_context = ""
            if patient_demographics:
                age = patient_demographics.get("age")
                gender = patient_demographics.get("gender")
                smoking = patient_demographics.get("smoking_history")
                
                demo_parts = []
                if age:
                    demo_parts.append(f"age {age}")
                if gender:
                    demo_parts.append(gender.lower())
                if smoking:
                    demo_parts.append(f"smoking history: {smoking}")
                
                if demo_parts:
                    demographic_context = f" in {', '.join(demo_parts)} patient"
            
            clinical_query = f"cancer referral criteria for {symptoms_text}{demographic_context}"
            
            logger.info(f"Building clinical context for: {clinical_query}")
            
            # Search for relevant guidelines
            search_results = await self.search_and_format(
                query=clinical_query,
                top_k=top_k,
                format_for_llm=True,
                include_citations=True
            )
            
            # Add clinical-specific formatting
            clinical_context = {
                "patient_symptoms": patient_symptoms,
                "patient_demographics": patient_demographics,
                "clinical_query": clinical_query,
                "guideline_context": search_results["context"],
                "citations": search_results["citations"],
                "num_relevant_guidelines": search_results["num_results"]
            }
            
            return clinical_context
            
        except RAGPipelineError:
            raise
        except Exception as e:
            raise RAGPipelineError(f"Failed to build clinical context: {e}")
    
    async def initialize_from_pdf_chunks(
        self,
        pdf_chunks: List[TextChunk],
        batch_size: int = 10
    ) -> None:
        """
        Initialize the vector store with PDF chunks.
        
        Args:
            pdf_chunks: List of TextChunk objects from PDF parser
            batch_size: Batch size for embedding generation
            
        Raises:
            RAGPipelineError: If initialization fails
        """
        if not pdf_chunks:
            raise RAGPipelineError("No PDF chunks provided for initialization")
        
        try:
            logger.info(f"Initializing vector store with {len(pdf_chunks)} chunks")
            
            # Extract text content for embedding
            texts = [chunk.content for chunk in pdf_chunks]
            
            # Generate embeddings in batches
            logger.info("Generating embeddings for PDF chunks...")
            embeddings = await self.embedding_service.generate_embeddings_batch(
                texts=texts,
                task_type="RETRIEVAL_DOCUMENT",
                batch_size=batch_size
            )
            
            # Add documents to vector store
            logger.info("Adding documents to vector store...")
            await self.vector_store.add_documents(pdf_chunks, embeddings)
            
            # Persist the index
            self.vector_store.persist_index()
            
            logger.info("Successfully initialized RAG pipeline with PDF content")
            
        except (EmbeddingServiceError, VectorStoreError) as e:
            raise RAGPipelineError(f"Failed to initialize from PDF chunks: {e}")
        except Exception as e:
            raise RAGPipelineError(f"Unexpected error during initialization: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of the RAG pipeline.
        
        Returns:
            Dictionary with health status of all components
        """
        health_status = {
            "pipeline_healthy": True,
            "components": {}
        }
        
        try:
            # Check embedding service
            embedding_healthy = await self.embedding_service.health_check()
            health_status["components"]["embedding_service"] = {
                "healthy": embedding_healthy,
                "model_info": self.embedding_service.get_model_info()
            }
            
            # Check vector store
            vector_store_healthy = await self.vector_store.health_check()
            vector_store_stats = self.vector_store.get_collection_stats()
            health_status["components"]["vector_store"] = {
                "healthy": vector_store_healthy,
                "stats": vector_store_stats
            }
            
            # Overall health
            health_status["pipeline_healthy"] = embedding_healthy and vector_store_healthy
            
            # Test end-to-end functionality if both components are healthy
            if health_status["pipeline_healthy"]:
                try:
                    test_chunks = await self.retrieve_relevant_chunks("test query", top_k=1)
                    health_status["end_to_end_test"] = {
                        "success": True,
                        "retrieved_chunks": len(test_chunks)
                    }
                except Exception as e:
                    health_status["end_to_end_test"] = {
                        "success": False,
                        "error": str(e)
                    }
                    health_status["pipeline_healthy"] = False
            
            return health_status
            
        except Exception as e:
            health_status["pipeline_healthy"] = False
            health_status["error"] = str(e)
            return health_status
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the RAG pipeline configuration.
        
        Returns:
            Dictionary with pipeline statistics
        """
        return {
            "default_top_k": self.default_top_k,
            "similarity_threshold": self.similarity_threshold,
            "embedding_dimension": self.embedding_service.get_embedding_dimension(),
            "vector_store_stats": self.vector_store.get_collection_stats()
        }
    
    async def generate_chat_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        top_k: int = 5
    ) -> GeneratedResponse:
        """
        Generate a chat response using retrieved NG12 content and Gemini.
        
        Args:
            query: User's chat query
            conversation_history: Previous conversation context
            top_k: Number of relevant chunks to retrieve
            
        Returns:
            GeneratedResponse with content and citations
            
        Raises:
            RAGPipelineError: If response generation fails
        """
        try:
            # Retrieve relevant chunks
            chunks = await self.retrieve_relevant_chunks(query, top_k)
            
            # Format context for LLM
            guideline_context = self.format_context_for_llm(chunks)
            
            # Generate response using Gemini (if available)
            if self.gemini_agent:
                response_content = await self.gemini_agent.generate_chat_response(
                    user_query=query,
                    guideline_context=guideline_context,
                    conversation_history=conversation_history
                )
            else:
                # Fallback response if no Gemini agent
                if chunks:
                    response_content = f"Based on the NG12 guidelines, here is the relevant information:\n\n{guideline_context}"
                else:
                    response_content = "I cannot find support in NG12 for that query. No relevant guidelines were found."
            
            # Format citations
            citations = self.format_citations(chunks)
            
            return GeneratedResponse(
                content=response_content,
                citations=citations,
                model_metadata={
                    "query": query,
                    "num_chunks_retrieved": len(chunks),
                    "has_gemini_agent": self.gemini_agent is not None
                }
            )
            
        except RAGPipelineError:
            raise
        except Exception as e:
            raise RAGPipelineError(f"Failed to generate chat response: {e}")
    
    async def generate_assessment_response(
        self,
        patient_data: str,
        clinical_context: Dict[str, Any]
    ) -> GeneratedResponse:
        """
        Generate an assessment response using clinical context and Gemini.
        
        Args:
            patient_data: Formatted patient information
            clinical_context: Clinical context from build_clinical_context
            
        Returns:
            GeneratedResponse with assessment and citations
            
        Raises:
            RAGPipelineError: If assessment generation fails
        """
        try:
            guideline_context = clinical_context.get("guideline_context", "")
            citations = clinical_context.get("citations", [])
            
            # Generate assessment using Gemini (if available)
            if self.gemini_agent:
                response_content = await self.gemini_agent.generate_clinical_assessment(
                    patient_data=patient_data,
                    guideline_context=guideline_context
                )
            else:
                # Fallback assessment if no Gemini agent
                if citations:
                    response_content = f"Assessment: No Action\nReasoning: Unable to generate clinical assessment without Gemini agent. Please review the following NG12 guidelines manually:\n\n{guideline_context}\nCitations: See retrieved guideline sections above."
                else:
                    response_content = "Assessment: No Action\nReasoning: No relevant NG12 guidelines found for the patient's symptoms.\nCitations: None available."
            
            return GeneratedResponse(
                content=response_content,
                citations=citations,
                model_metadata={
                    "patient_query": clinical_context.get("clinical_query", ""),
                    "num_guidelines": clinical_context.get("num_relevant_guidelines", 0),
                    "has_gemini_agent": self.gemini_agent is not None
                }
            )
            
        except Exception as e:
            raise RAGPipelineError(f"Failed to generate assessment response: {e}")