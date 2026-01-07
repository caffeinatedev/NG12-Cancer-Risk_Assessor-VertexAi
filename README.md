# NG12 Cancer Risk Assessor

A clinical reasoning agent that combines structured patient data with unstructured clinical guidelines to provide cancer risk assessments and conversational clinical support using **Google Vertex AI (Gemini 1.5)** and a unified **RAG Pipeline**.

## 🏗️ Architecture

The system follows a modular architecture with a clear separation of concerns:
- **API Layer**: FastAPI service providing endpoints for assessment and chat.
- **Business Logic**: 
  - `AssessmentEngine`: Orchestrates patient data retrieval and clinical reasoning.
  - `ChatEngine`: Manages multi-turn conversation sessions.
- **Data Layer**: 
  - `RAGPipeline`: Shared retrieval logic using Vertex AI Embeddings and ChromaDB.
  - `PDFParser`: Downloads and chunks the NICE NG12 Guidelines.
  - `PatientLoader`: Simulates database retrieval for structured patient data.

## 🚀 Quick Start (Docker)

The fastest way to run the full system is using Docker Compose. This automatically handles the API service, the static frontend, and data initialization.

1.  **Configure Environment**:
    Create a `.env` file from the template and add your Google Cloud project details and Service Account Key.
    ```bash
    cp .env.template .env
    ```
2.  **Start Services**:
    ```bash
    docker compose up --build -d
    ```
3.  **Access the Application**:
    - **Web Interface**: [http://localhost:8000](http://localhost:8000)
    - **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🛠️ Local Development Setup

If you prefer to run the service outside of Docker:

### 1. Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Initialize the Vector Store
Before running the app, you must parse the NG12 PDF and build the vector index:
```bash
python scripts/initialize_vector_store.py
```

### 3. Start the Server
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📡 API Endpoints

### Patient Risk Assessment
- **`POST /assess`**: Accepts a `patient_id`. 
  - **Tool Use**: The agent uses **Vertex AI Function Calling** to dynamically fetch structured data (Age, Symptoms) from the simulated database.
  - **Output**: Returns a JSON response with the assessment level ("Urgent Referral", etc.) and specific NG12 citations.

### Conversational AI (Chat Mode)
- **`POST /chat`**: Supports multi-turn conversation about clinical guidelines.
- **`GET /chat/{session_id}/history`**: Retrieves conversation history.
- **`DELETE /chat/{session_id}`**: Clears session data.

## 🧠 Prompt Engineering
Detailed documentation of the system prompts, grounding strategies, and hallucination prevention techniques can be found in [PROMPTS.md](PROMPTS.md).

## 🧪 Testing
Run the basic API integration test:
```bash
python test_assessment_api.py
```

---
*This project is submitted as part of a technical assessment for C the Signs.*
