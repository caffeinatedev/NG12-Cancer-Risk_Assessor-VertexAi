"""
Vector store implementation for the NG12 Cancer Risk Assessor.
Provides semantic search over NG12 guideline embeddings using ChromaDB.
"""
import logging
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import uuid

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from .models import DocumentMetadata, TextChunk


logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Custom exception for vector store errors."""
    pass


class SearchResult:
    """Result from vector similarity search."""
    
    def __init__(
        self,
        chunk_id: str,
        content: str,
        metadata: DocumentMetadata,
        similarity_score: float
    ):
        self.chunk_id = chunk_id
        self.content = content
        self.metadata = metadata
        self.similarity_score = similarity_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata.dict(),
            "similarity_score": self.similarity_score
        }


class VectorStore:
    """
    Vector store implementation using ChromaDB for semantic search.
    
    Stores NG12 guideline chunks with embeddings and metadata for
    efficient similarity search and retrieval.
    """
    
    def __init__(
        self,
        store_path: str = "./data/vector_store",
        collection_name: str = "ng12_guidelines"
    ):
        """
        Initialize the VectorStore.
        
        Args:
            store_path: Path to store the ChromaDB database
            collection_name: Name of the collection to store documents
        """
        self.store_path = Path(store_path)
        self.collection_name = collection_name
        
        # Create directory if it doesn't exist
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self._client: Optional[chromadb.Client] = None
        self._collection: Optional[chromadb.Collection] = None
        
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            # Create ChromaDB client with persistent storage
            self._client = chromadb.PersistentClient(
                path=str(self.store_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            # Note: We'll use external embeddings, so no embedding function needed
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "NG12 Cancer Guidelines chunks with embeddings"}
            )
            
            logger.info(f"Initialized ChromaDB collection '{self.collection_name}' at {self.store_path}")
            
        except Exception as e:
            raise VectorStoreError(f"Failed to initialize ChromaDB: {e}")
    
    async def add_documents(self, chunks: List[TextChunk], embeddings: List[List[float]]) -> None:
        """
        Add document chunks with their embeddings to the vector store.
        
        Args:
            chunks: List of TextChunk objects to add
            embeddings: Corresponding embeddings for each chunk
            
        Raises:
            VectorStoreError: If adding documents fails
        """
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                f"Number of chunks ({len(chunks)}) must match number of embeddings ({len(embeddings)})"
            )
        
        if not chunks:
            logger.warning("No chunks provided to add to vector store")
            return
        
        try:
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            embeddings_list = []
            
            for chunk, embedding in zip(chunks, embeddings):
                # Create document metadata for ChromaDB
                metadata = {
                    "chunk_id": chunk.chunk_id,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "document_source": "NG12 PDF"
                }
                
                ids.append(chunk.chunk_id)
                documents.append(chunk.content)
                metadatas.append(metadata)
                embeddings_list.append(embedding)
            
            # Add to ChromaDB collection
            self._collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings_list
            )
            
            logger.info(f"Added {len(chunks)} documents to vector store")
            
        except Exception as e:
            raise VectorStoreError(f"Failed to add documents to vector store: {e}")
    
    async def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Perform similarity search using query embedding.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of SearchResult objects ranked by similarity
            
        Raises:
            VectorStoreError: If search fails
        """
        if not query_embedding:
            raise VectorStoreError("Query embedding cannot be empty")
        
        try:
            # Perform similarity search
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, 100),  # ChromaDB limit
                where=filter_metadata,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert results to SearchResult objects
            search_results = []
            
            if results["ids"] and len(results["ids"]) > 0:
                ids = results["ids"][0]
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = results["distances"][0]
                
                for i in range(len(ids)):
                    # Convert distance to similarity score (ChromaDB uses L2 distance)
                    # For L2 distance, similarity = 1 / (1 + distance)
                    # But we need to handle very small distances better
                    distance = distances[i]
                    if distance < 0.001:
                        similarity_score = 1.0 - distance  # For very small distances
                    else:
                        similarity_score = 1.0 / (1.0 + distance)
                    
                    # Create DocumentMetadata object
                    metadata = DocumentMetadata(
                        chunk_id=metadatas[i]["chunk_id"],
                        page_number=metadatas[i]["page_number"],
                        section_title=metadatas[i]["section_title"],
                        excerpt=documents[i][:200] + "..." if len(documents[i]) > 200 else documents[i],
                        document_source=metadatas[i].get("document_source", "NG12 PDF")
                    )
                    
                    search_result = SearchResult(
                        chunk_id=ids[i],
                        content=documents[i],
                        metadata=metadata,
                        similarity_score=similarity_score
                    )
                    
                    search_results.append(search_result)
            
            logger.debug(f"Found {len(search_results)} results for similarity search")
            return search_results
            
        except Exception as e:
            raise VectorStoreError(f"Similarity search failed: {e}")
    
    def get_document_by_id(self, chunk_id: str) -> Optional[SearchResult]:
        """
        Retrieve a specific document by its chunk ID.
        
        Args:
            chunk_id: Unique chunk identifier
            
        Returns:
            SearchResult object or None if not found
        """
        try:
            results = self._collection.get(
                ids=[chunk_id],
                include=["documents", "metadatas"]
            )
            
            if results["ids"] and len(results["ids"]) > 0:
                metadata = DocumentMetadata(
                    chunk_id=results["metadatas"][0]["chunk_id"],
                    page_number=results["metadatas"][0]["page_number"],
                    section_title=results["metadatas"][0]["section_title"],
                    excerpt=results["documents"][0][:200] + "..." if len(results["documents"][0]) > 200 else results["documents"][0],
                    document_source=results["metadatas"][0].get("document_source", "NG12 PDF")
                )
                
                return SearchResult(
                    chunk_id=chunk_id,
                    content=results["documents"][0],
                    metadata=metadata,
                    similarity_score=1.0  # Perfect match for direct retrieval
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document by ID {chunk_id}: {e}")
            return None
    
    def get_documents_by_page(self, page_number: int) -> List[SearchResult]:
        """
        Get all documents from a specific page.
        
        Args:
            page_number: Page number to filter by
            
        Returns:
            List of SearchResult objects from the page
        """
        try:
            results = self._collection.get(
                where={"page_number": page_number},
                include=["documents", "metadatas"]
            )
            
            search_results = []
            
            if results["ids"]:
                for i in range(len(results["ids"])):
                    metadata = DocumentMetadata(
                        chunk_id=results["metadatas"][i]["chunk_id"],
                        page_number=results["metadatas"][i]["page_number"],
                        section_title=results["metadatas"][i]["section_title"],
                        excerpt=results["documents"][i][:200] + "..." if len(results["documents"][i]) > 200 else results["documents"][i],
                        document_source=results["metadatas"][i].get("document_source", "NG12 PDF")
                    )
                    
                    search_result = SearchResult(
                        chunk_id=results["ids"][i],
                        content=results["documents"][i],
                        metadata=metadata,
                        similarity_score=1.0
                    )
                    
                    search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to get documents by page {page_number}: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self._collection.count()
            
            # Get sample of documents to analyze
            sample_results = self._collection.peek(limit=10)
            
            stats = {
                "total_documents": count,
                "collection_name": self.collection_name,
                "store_path": str(self.store_path)
            }
            
            if sample_results["metadatas"]:
                # Analyze page distribution
                pages = [meta.get("page_number", 0) for meta in sample_results["metadatas"]]
                stats["sample_pages"] = sorted(set(pages))
                
                # Analyze section distribution
                sections = [meta.get("section_title", "Unknown") for meta in sample_results["metadatas"]]
                stats["sample_sections"] = list(set(sections))
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    def delete_collection(self) -> None:
        """
        Delete the entire collection and all its data.
        
        Warning: This operation cannot be undone!
        """
        try:
            self._client.delete_collection(name=self.collection_name)
            logger.info(f"Deleted collection '{self.collection_name}'")
            
            # Reinitialize collection
            self._initialize_client()
            
        except Exception as e:
            raise VectorStoreError(f"Failed to delete collection: {e}")
    
    def persist_index(self) -> None:
        """
        Persist the vector index to disk.
        
        Note: ChromaDB with PersistentClient automatically persists data.
        This method is provided for compatibility.
        """
        try:
            # ChromaDB automatically persists with PersistentClient
            logger.info("Vector store data is automatically persisted")
            
        except Exception as e:
            logger.error(f"Error during persist operation: {e}")
    
    def load_index(self) -> None:
        """
        Load the vector index from disk.
        
        Note: ChromaDB with PersistentClient automatically loads data.
        This method is provided for compatibility.
        """
        try:
            # ChromaDB automatically loads with PersistentClient
            stats = self.get_collection_stats()
            logger.info(f"Vector store loaded with {stats.get('total_documents', 0)} documents")
            
        except Exception as e:
            logger.error(f"Error during load operation: {e}")
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the vector store.
        
        Returns:
            True if vector store is healthy, False otherwise
        """
        try:
            # Test basic operations
            count = self._collection.count()
            logger.debug(f"Vector store health check: {count} documents")
            return True
            
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return False
    
    def export_data(self, output_path: str) -> None:
        """
        Export vector store data to JSON file for backup/analysis.
        
        Args:
            output_path: Path to save the exported data
        """
        try:
            # Get all data from collection
            results = self._collection.get(
                include=["documents", "metadatas", "embeddings"]
            )
            
            export_data = {
                "collection_name": self.collection_name,
                "total_documents": len(results["ids"]) if results["ids"] else 0,
                "documents": []
            }
            
            if results["ids"]:
                for i in range(len(results["ids"])):
                    doc_data = {
                        "id": results["ids"][i],
                        "content": results["documents"][i],
                        "metadata": results["metadatas"][i],
                        "embedding": results["embeddings"][i] if results["embeddings"] else None
                    }
                    export_data["documents"].append(doc_data)
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {export_data['total_documents']} documents to {output_path}")
            
        except Exception as e:
            raise VectorStoreError(f"Failed to export data: {e}")