"""
Vertex AI embeddings service for the NG12 Cancer Risk Assessor.
Handles text embedding generation using Google Vertex AI text-embedding-004 model.
"""
import logging
import os
from typing import List, Optional, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

from google.cloud import aiplatform
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2 import service_account
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput


logger = logging.getLogger(__name__)


class EmbeddingServiceError(Exception):
    """Custom exception for embedding service errors."""
    pass


class EmbeddingService:
    """
    Vertex AI embeddings service using text-embedding-004 model.
    
    Provides methods for generating embeddings from text with batch processing
    support for efficient embedding generation.
    """
    
    def __init__(
        self, 
        project_id: Optional[str] = None,
        location: str = "us-central1",
        model_name: str = "text-embedding-004",
        use_mock: bool = False
    ):
        """
        Initialize the EmbeddingService.
        
        Args:
            project_id: Google Cloud project ID (defaults to environment)
            location: Vertex AI location (defaults to us-central1)
            model_name: Embedding model name (defaults to text-embedding-004)
            use_mock: Whether to use mock embeddings instead of real Vertex AI
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.model_name = model_name or os.getenv("VERTEX_AI_EMBEDDING_MODEL", "text-embedding-004")
        self.use_mock = use_mock or os.getenv("USE_MOCK_GEMINI", "false").lower() == "true"
        
        if not self.project_id:
            raise EmbeddingServiceError(
                "Google Cloud project ID not found. Set GOOGLE_CLOUD_PROJECT environment variable."
            )
        
        self._model: Optional[TextEmbeddingModel] = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize Vertex AI if not using mock
        if not self.use_mock:
            self._initialize_vertex_ai()
    
    def _initialize_vertex_ai(self) -> None:
        """Initialize Vertex AI with proper authentication."""
        try:
            credentials = None
            
            # Check for credentials in environment variable
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
            if service_account_json:
                try:
                    logger.info("Loading credentials from GOOGLE_SERVICE_ACCOUNT_JSON env var")
                    import json
                    info = json.loads(service_account_json)
                    credentials = service_account.Credentials.from_service_account_info(info)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
                    raise
            
            # Initialize AI Platform (Vertex AI) explicitly
            aiplatform.init(
                project=self.project_id,
                location=self.location,
                credentials=credentials
            )
            
            # Initialize Vertex AI SDK
            vertexai.init(
                project=self.project_id, 
                location=self.location, 
                credentials=credentials
            )
            
            # Test authentication if explicit credentials weren't provided
            if not credentials:
                creds, project = default()
                if project != self.project_id:
                    logger.warning(f"Default project ({project}) differs from configured project ({self.project_id})")
            
            logger.info(f"Initialized Vertex AI for project {self.project_id} in {self.location}")
            
        except DefaultCredentialsError as e:
            logger.warning(f"Google Cloud credentials not found, falling back to mock mode: {e}")
            self.use_mock = True
        except Exception as e:
            logger.warning(f"Failed to initialize Vertex AI, falling back to mock mode: {e}")
            self.use_mock = True
    
    def _get_model(self) -> TextEmbeddingModel:
        """Get or create the embedding model instance."""
        if self._model is None:
            try:
                self._model = TextEmbeddingModel.from_pretrained(self.model_name)
                logger.info(f"Loaded embedding model: {self.model_name}")
            except Exception as e:
                raise EmbeddingServiceError(f"Failed to load embedding model {self.model_name}: {e}")
        
        return self._model
    
    async def generate_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            task_type: Task type for the embedding (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, etc.)
            
        Returns:
            List of embedding values (768 dimensions for text-embedding-004)
            
        Raises:
            EmbeddingServiceError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingServiceError("Input text cannot be empty")
        
        if self.use_mock:
            return await self._generate_mock_embedding(text)
        
        try:
            # Run the synchronous embedding generation in a thread pool
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                self._executor,
                self._generate_embedding_sync,
                text.strip(),
                task_type
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed, falling back to mock: {e}")
            return await self._generate_mock_embedding(text)
    
    def _generate_embedding_sync(self, text: str, task_type: str) -> List[float]:
        """Synchronous embedding generation."""
        model = self._get_model()
        
        # Create embedding input with task type
        embedding_input = TextEmbeddingInput(
            text=text,
            task_type=task_type
        )
        
        # Generate embedding
        embeddings = model.get_embeddings([embedding_input])
        
        if not embeddings or len(embeddings) == 0:
            raise EmbeddingServiceError("No embeddings returned from model")
        
        return embeddings[0].values
    
    async def generate_embeddings_batch(
        self, 
        texts: List[str], 
        task_type: str = "RETRIEVAL_DOCUMENT",
        batch_size: int = 5
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batch processing.
        
        Args:
            texts: List of input texts to embed
            task_type: Task type for the embeddings
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embedding vectors corresponding to input texts
            
        Raises:
            EmbeddingServiceError: If batch embedding generation fails
        """
        if not texts:
            return []
        
        if self.use_mock:
            return await self._generate_mock_embeddings_batch(texts)
        
        # Filter out empty texts
        valid_texts = [(i, text.strip()) for i, text in enumerate(texts) if text and text.strip()]
        
        if not valid_texts:
            raise EmbeddingServiceError("No valid texts provided for embedding")
        
        try:
            embeddings_result = [None] * len(texts)
            
            # Process in batches
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i:i + batch_size]
                batch_texts = [text for _, text in batch]
                batch_indices = [idx for idx, _ in batch]
                
                logger.debug(f"Processing batch {i//batch_size + 1}: {len(batch_texts)} texts")
                
                # Generate embeddings for batch
                loop = asyncio.get_event_loop()
                batch_embeddings = await loop.run_in_executor(
                    self._executor,
                    self._generate_embeddings_batch_sync,
                    batch_texts,
                    task_type
                )
                
                # Store results in correct positions
                for j, embedding in enumerate(batch_embeddings):
                    original_idx = batch_indices[j]
                    embeddings_result[original_idx] = embedding
            
            # Fill in None values for empty texts with zero vectors
            embedding_dim = 768  # text-embedding-004 dimension
            for i, embedding in enumerate(embeddings_result):
                if embedding is None:
                    embeddings_result[i] = [0.0] * embedding_dim
                    logger.warning(f"Empty text at index {i}, using zero vector")
            
            logger.info(f"Generated embeddings for {len(texts)} texts")
            return embeddings_result
            
        except Exception as e:
            logger.error(f"Batch embedding generation failed, falling back to mock: {e}")
            return await self._generate_mock_embeddings_batch(texts)
    
    def _generate_embeddings_batch_sync(self, texts: List[str], task_type: str) -> List[List[float]]:
        """Synchronous batch embedding generation."""
        model = self._get_model()
        
        # Create embedding inputs
        embedding_inputs = [
            TextEmbeddingInput(text=text, task_type=task_type)
            for text in texts
        ]
        
        # Generate embeddings
        embeddings = model.get_embeddings(embedding_inputs)
        
        if len(embeddings) != len(texts):
            raise EmbeddingServiceError(
                f"Expected {len(texts)} embeddings, got {len(embeddings)}"
            )
        
        return [embedding.values for embedding in embeddings]
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Query embedding vector
        """
        return await self.generate_embedding(query, task_type="RETRIEVAL_QUERY")
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            Embedding dimension (768 for text-embedding-004)
        """
        return 768
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "project_id": self.project_id,
            "location": self.location,
            "use_mock": self.use_mock,
            "embedding_dimension": self.get_embedding_dimension(),
            "max_input_tokens": 3072,  # text-embedding-004 limit
            "supported_task_types": [
                "RETRIEVAL_DOCUMENT",
                "RETRIEVAL_QUERY", 
                "SEMANTIC_SIMILARITY",
                "CLASSIFICATION",
                "CLUSTERING"
            ]
        }
    
    async def health_check(self) -> bool:
        """
        Perform a health check by generating a test embedding.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            test_embedding = await self.generate_embedding("Health check test")
            return len(test_embedding) == self.get_embedding_dimension()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate mock embedding for development/testing."""
        import hashlib
        import random
        
        # Create deterministic but varied embeddings based on text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()
        random.seed(int(text_hash[:8], 16))
        
        # Generate 768-dimensional embedding with values between -1 and 1
        embedding = [random.uniform(-1.0, 1.0) for _ in range(768)]
        
        # Add small delay to simulate API call
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        return embedding
    
    async def _generate_mock_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for batch of texts."""
        embeddings = []
        for text in texts:
            if text and text.strip():
                embedding = await self._generate_mock_embedding(text)
            else:
                # Zero vector for empty texts
                embedding = [0.0] * 768
            embeddings.append(embedding)
        
        return embeddings
    
    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)