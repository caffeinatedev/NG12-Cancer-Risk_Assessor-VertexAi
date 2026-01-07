#!/usr/bin/env python3
"""
Initialize the vector store with NG12 guidelines.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_parser import PDFParser
from src.embedding_service import EmbeddingService
from src.vector_store import VectorStore
from src.rag_pipeline import RAGPipeline
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    print("🏥 Initializing NG12 Vector Store")
    print("=" * 50)
    
    try:
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

        # 1. Parse PDF (will use mock content if download fails)
        print("1. Parsing NG12 PDF...")
        pdf_parser = PDFParser(download_dir="data")
        pdf_parser.download_ng12_pdf(use_mock_on_failure=True)
        chunks = pdf_parser.extract_text_with_metadata()
        print(f"   ✓ Extracted {len(chunks)} chunks")
        
        # 2. Initialize services
        print("2. Initializing services...")
        embedding_service = EmbeddingService(
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            use_mock=os.getenv("USE_MOCK_GEMINI", "false").lower() == "true"
        )
        
        vector_store = VectorStore(
            store_path=os.getenv("VECTOR_STORE_PATH", "./data/vector_store")
        )
        print("   ✓ Services initialized")
        
        # 3. Generate embeddings and populate vector store
        print("3. Generating embeddings (this may take a few minutes)...")
        texts = [chunk.content for chunk in chunks]
        embeddings = await embedding_service.generate_embeddings_batch(
            texts=texts,
            task_type="RETRIEVAL_DOCUMENT",
            batch_size=10
        )
        print(f"   ✓ Generated {len(embeddings)} embeddings")
        
        # 4. Add to vector store
        print("4. Adding to vector store...")
        await vector_store.add_documents(chunks, embeddings)
        vector_store.persist_index()
        print(f"   ✓ Vector store populated")
        
        # 5. Verify
        print("5. Verifying...")
        stats = vector_store.get_collection_stats()
        print(f"   ✓ Total documents: {stats['total_documents']}")
        
        print("\n✅ Vector store initialization complete!")
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)