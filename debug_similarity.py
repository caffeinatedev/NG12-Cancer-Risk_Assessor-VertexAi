#!/usr/bin/env python3
"""
Debug similarity scores in the RAG pipeline.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.rag_pipeline import RAGPipeline
from src.embedding_service import EmbeddingService
from src.vector_store import VectorStore
import os
from dotenv import load_dotenv

load_dotenv()

async def test_similarity():
    print("🔍 Debugging RAG Pipeline Similarity Scores")
    print("=" * 50)
    
    try:
        # Initialize services
        embedding_service = EmbeddingService(
            project_id=os.getenv('GOOGLE_CLOUD_PROJECT'),
            use_mock=False
        )
        vector_store = VectorStore()
        
        # Check vector store stats
        stats = vector_store.get_collection_stats()
        print(f"Vector store stats: {stats}")
        
        # Test queries that should match NG12 content
        test_queries = [
            "hemoptysis cough lung cancer referral",
            "chest pain shortness of breath cancer",
            "breast lump cancer referral",
            "weight loss abdominal pain colorectal",
            "urgent referral suspected cancer"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            
            # Generate query embedding
            query_embedding = await embedding_service.generate_query_embedding(query)
            print(f"   Query embedding: {len(query_embedding)} dimensions")
            
            # Search with no threshold to see actual scores
            results = await vector_store.similarity_search(query_embedding, top_k=5)
            
            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results):
                print(f"   {i+1}. Score: {result.similarity_score:.6f}")
                print(f"      Content: {result.content[:150]}...")
                print(f"      Page: {result.metadata.page_number}, Section: {result.metadata.section_title}")
                print()
        
        # Test with RAG pipeline to see threshold filtering
        print("\n🔧 Testing RAG Pipeline with current threshold...")
        rag_pipeline = RAGPipeline(
            embedding_service=embedding_service,
            vector_store=vector_store,
            similarity_threshold=0.1  # Current threshold
        )
        
        for query in test_queries[:2]:  # Test first 2 queries
            print(f"\n📋 RAG Pipeline query: '{query}'")
            chunks = await rag_pipeline.retrieve_relevant_chunks(query, top_k=5)
            print(f"   Retrieved chunks after threshold filtering: {len(chunks)}")
            
            if chunks:
                for i, chunk in enumerate(chunks):
                    print(f"   {i+1}. Score: {chunk.similarity_score:.6f} - {chunk.content[:100]}...")
            else:
                print("   ❌ No chunks passed the similarity threshold!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_similarity())