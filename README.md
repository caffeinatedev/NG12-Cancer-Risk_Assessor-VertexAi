# NG12 Cancer Risk Assessor

A clinical reasoning agent that combines structured patient data with unstructured clinical guidelines to provide cancer risk assessments and conversational clinical support using **Google Vertex AI (Gemini 2.5 Flash)** and a unified **RAG Pipeline**.

> **Technical Assessment Submission** for C the Signs  
> **Deadline**: January 7, 2026 | **Time Investment**: ~5-7 hours

---

## 📋 **Deliverables Overview** | [Demo Video](https://app.arcade.software/share/EzMmLOS5h5cPjpTmrQXB)


This project implements **both required parts** of the technical assessment:

### ✅ **Part 1: Clinical Decision Support Agent**
- **FastAPI Service** with Docker containerization
- **Tool Use (Function Calling)**: Agent dynamically fetches patient data via `get_patient_data` tool
- **RAG Pipeline**: Vector search over NG12 guidelines using Vertex AI Embeddings + ChromaDB
- **Clinical Reasoning**: Synthesizes patient symptoms with guidelines to classify risk
- **JSON Output**: Structured responses with specific NG12 citations
- **Minimal UI**: Web interface for patient assessment

**Key Files**:
- `src/assessment_engine.py` - Clinical decision orchestration
- `src/gemini_agent.py` - Gemini 2.5 Flash with Function Calling
- `src/rag_pipeline.py` - Shared RAG pipeline
- `frontend/index.html` - Assessment UI (tab 1)

### ✅ **Part 2: Conversational AI (Chat Mode)**
- **Reuses Vector Store**: Same RAG pipeline from Part 1
- **Multi-turn Conversations**: Session-managed chat with history
- **Grounding & Guardrails**: All responses cite NG12 guidelines
- **REST API Endpoints**: POST `/chat`, GET `/chat/{id}/history`, DELETE `/chat/{id}`
- **Chat UI**: Interactive chat interface

**Key Files**:
- `src/chat_engine.py` - Conversation management
- `frontend/index.html` - Chat UI (tab 2)
- `PROMPTS.md` - Comprehensive prompt engineering strategy

---

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Service                        │
│  ┌──────────────────┐          ┌──────────────────┐        │
│  │ Assessment Engine│          │   Chat Engine    │        │
│  │  (Part 1)        │          │   (Part 2)       │        │
│  └────────┬─────────┘          └────────┬─────────┘        │
│           │                              │                  │
│           └──────────┬───────────────────┘                  │
│                      │                                      │
│              ┌───────▼────────┐                             │
│              │  RAG Pipeline  │  (Shared)                   │
│              │  - Embeddings  │                             │
│              │  - Vector Store│                             │
│              │  - Gemini LLM  │                             │
│              └───────┬────────┘                             │
└──────────────────────┼──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌────▼─────────┐
│ Vertex AI    │ │ ChromaDB   │ │ Patient Data │
│ Embeddings   │ │ Vector DB  │ │ (JSON)       │
└──────────────┘ └────────────┘ └──────────────┘
```

**Components**:
- **API Layer**: FastAPI service (`src/main.py`)
- **Business Logic**: 
  - `AssessmentEngine` - Orchestrates patient data retrieval and clinical reasoning
  - `ChatEngine` - Manages multi-turn conversation sessions
- **Data Layer**: 
  - `RAGPipeline` - Shared retrieval logic using Vertex AI Embeddings and ChromaDB
  - `PDFParser` - Downloads and chunks the NICE NG12 Guidelines
  - `PatientLoader` - Simulates database retrieval for structured patient data

---

## 🚀 **Quick Start Guide**

### **Prerequisites**

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- Google Cloud Project with Vertex AI API enabled
- Service Account with appropriate permissions

---

## 🔐 **Google Cloud Setup**

### **Step 1: Create a Google Cloud Project**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your **Project ID** (e.g., `my-ng12-project`)

### **Step 2: Enable Required APIs**

```bash
gcloud services enable aiplatform.googleapis.com
gcloud services enable compute.googleapis.com
```

Or enable via Console:
- Navigate to **APIs & Services** → **Library**
- Search for and enable:
  - **Vertex AI API**
  - **Cloud AI Platform API**

### **Step 3: Create Service Account**

#### **Option A: Using gcloud CLI**

```bash
# Create service account
gcloud iam service-accounts create ng12-service-account \
    --display-name="NG12 Assessor Service Account"

# Grant necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:ng12-service-account@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Create and download key
gcloud iam service-accounts keys create ng12-service-account.json \
    --iam-account=ng12-service-account@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

#### **Option B: Using Google Cloud Console**

1. Navigate to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
   - Name: `ng12-service-account`
   - Description: `Service account for NG12 Cancer Risk Assessor`
3. Grant roles:
   - **Vertex AI User** (`roles/aiplatform.user`)
4. Click **Create Key** → Select **JSON** → Download
5. Rename the downloaded file to `ng12-service-account.json`

### **Step 4: Place Credentials in Project**

```bash
# Place the service account JSON in the project root
# (This file is already in .gitignore)
mv ~/Downloads/ng12-service-account.json ./ng12-service-account.json
```

**⚠️ IMPORTANT**: Never commit this file to Git! It's already listed in `.gitignore`.

---

## ⚙️ **Environment Configuration**

### **Step 1: Create `.env` File**

```bash
cp .env.template .env
```

### **Step 2: Edit `.env` File**

Open `.env` and configure the following:

```bash
# ============================================
# Google Cloud Configuration
# ============================================

# Your Google Cloud Project ID (from Step 1)
GOOGLE_CLOUD_PROJECT=my-ng12-project

# Vertex AI location (default: us-central1)
GOOGLE_CLOUD_LOCATION=us-central1

# ============================================
# Credentials Configuration
# ============================================

# Path to your service account JSON file
# For Docker: /app/credentials.json (mounted volume)
# For Local: ./ng12-service-account.json
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json

# ============================================
# Model Configuration
# ============================================

# Gemini model for reasoning (default: gemini-2.5-flash)
VERTEX_AI_MODEL=gemini-2.5-flash

# Embedding model (default: text-embedding-004)
VERTEX_AI_EMBEDDING_MODEL=text-embedding-004

# ============================================
# Application Configuration
# ============================================

# API server configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Vector store settings
VECTOR_STORE_TYPE=chromadb
VECTOR_STORE_PATH=./data/vector_store

# NG12 PDF Configuration
NG12_PDF_URL=https://www.nice.org.uk/guidance/ng12/resources/suspected-cancer-recognition-and-referral-pdf-1837268071621
NG12_PDF_PATH=./data/ng12_guidelines.pdf

# Patient data location
PATIENT_DATA_PATH=./data/patients.json

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# ============================================
# Optional: Use Mock Mode (for testing without GCP)
# ============================================
# USE_MOCK_GEMINI=false
```

---

## 🐳 **Running with Docker** (Recommended)

### **Method 1: Docker Compose (Full Stack)**

This is the **easiest method** - it starts both the API service and frontend:

```bash
# Build and start all services
docker compose up --build -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

**Access Points**:
- 🌐 **Web Interface**: http://localhost:8000
- 📡 **API Documentation**: http://localhost:8000/docs
- 💓 **Health Check**: http://localhost:8000/health
- 🎨 **Frontend (via Nginx)**: http://localhost:3000

### **Method 2: Individual Docker Containers**

#### **Build the Image**

```bash
docker build -t ng12-assessor:latest .
```

#### **Run the Container**

```bash
docker run -d \
  --name ng12-assessor \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/ng12-service-account.json:/app/credentials.json:ro \
  --env-file .env \
  ng12-assessor:latest
```

#### **View Logs**

```bash
docker logs -f ng12-assessor
```

#### **Stop the Container**

```bash
docker stop ng12-assessor
docker rm ng12-assessor
```

---

## 💻 **Running Locally (Without Docker)**

### **Step 1: Set Up Python Environment**

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### **Step 2: Initialize Vector Store**

Before running the app, you **must** parse the NG12 PDF and build the vector index:

```bash
# Make sure your .env is configured with valid GCP credentials
python scripts/initialize_vector_store.py
```

**Expected Output**:
```
🏥 Initializing NG12 Vector Store
==================================================
1. Parsing NG12 PDF...
   ✓ Extracted 127 chunks
2. Initializing services...
   ✓ Services initialized
3. Generating embeddings (this may take a few minutes)...
   ✓ Generated 127 embeddings
4. Adding to vector store...
   ✓ Vector store populated
5. Verifying...
   ✓ Total documents: 127

✅ Vector store initialization complete!
```

### **Step 3: Start the Backend Server**

```bash
# Using uvicorn directly
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# OR using the convenience script
python start_server.py
```

**Expected Output**:
```
🏥 NG12 Cancer Risk Assessor
==================================================
Starting FastAPI server...

✅ All required files present

📋 Configuration:
   - Google Cloud Project: my-ng12-project
   - API Host: 0.0.0.0
   - API Port: 8000
   - Vector Store: ./data/vector_store

🌐 Server URLs:
   - Web Interface: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

🚀 Starting server...
   Press Ctrl+C to stop the server

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### **Step 4: Access the Application**

Open your browser and navigate to:

- 🌐 **Main Application**: http://localhost:8000
- 📡 **API Documentation (Swagger)**: http://localhost:8000/docs
- 📖 **ReDoc Documentation**: http://localhost:8000/redoc
- 💓 **Health Check**: http://localhost:8000/health

---

## 📡 **API Endpoints Reference**

### **Part 1: Patient Risk Assessment**

#### **POST /assess**
Assess cancer risk for a patient based on symptoms and NG12 guidelines.

**Request**:
```json
{
  "patient_id": "PT-101"
}
```

**Response**:
```json
{
  "patient_id": "PT-101",
  "assessment": "Urgent Referral",
  "reasoning": "Patient presents with unexplained hemoptysis...",
  "citations": [
    {
      "source": "NG12 PDF",
      "page": 23,
      "chunk_id": "ng12_0023_01",
      "excerpt": "Refer people aged 40 and over with unexplained haemoptysis...",
      "relevance_score": 0.92
    }
  ],
  "confidence_score": 0.89
}
```

#### **POST /assess/batch**
Assess multiple patients in a single request.

**Request**:
```json
["PT-101", "PT-102", "PT-103"]
```

### **Part 2: Conversational AI (Chat)**

#### **POST /chat**
Send a chat message about NG12 guidelines.

**Request**:
```json
{
  "session_id": "session_abc123",
  "message": "What are the lung cancer referral criteria?",
  "top_k": 5
}
```

**Response**:
```json
{
  "session_id": "session_abc123",
  "answer": "According to NG12 guidelines, urgent referral for lung cancer is recommended for...",
  "citations": [
    {
      "source": "NG12 PDF",
      "page": 15,
      "chunk_id": "ng12_0015_02",
      "excerpt": "Consider an urgent chest X-ray...",
      "relevance_score": 0.88
    }
  ],
  "timestamp": "2026-01-07T14:30:00Z"
}
```

#### **GET /chat/{session_id}/history**
Retrieve conversation history for a session.

#### **DELETE /chat/{session_id}**
Delete a chat session and clear its history.

---

## 🧪 **Testing**

### **Run Integration Tests**

```bash
# Make sure the server is running first
python test_assessment_api.py
```

**Expected Output**:
```
🏥 Testing NG12 Cancer Risk Assessment API
==================================================
1. Testing health endpoint...
   ✓ Health check: healthy
2. Testing assessment stats endpoint...
   ✓ Assessment stats retrieved
3. Testing individual patient assessments...
   Testing patient: PT-101
   ✓ Assessment: Urgent Referral
   ✓ Reasoning: Patient presents with unexplained hemoptysis...
   ✓ Citations: 3 found
   ✓ Confidence: 0.89
4. Testing batch assessment...
   ✓ Batch assessment completed: 3 results
5. Testing error handling...
   ✓ Correctly handled invalid patient ID (404)
==================================================
✅ Assessment API testing completed!
```

### **Manual Testing via Swagger UI**

1. Navigate to http://localhost:8000/docs
2. Try the following endpoints:
   - **GET /health** - Verify service is running
   - **POST /assess** - Test with `{"patient_id": "PT-101"}`
   - **POST /chat** - Test chat functionality

---

## 🤖 **GitHub Actions CI/CD**

This repository includes a comprehensive CI/CD pipeline with the following workflows:

### **1. Main CI/CD Pipeline** (`.github/workflows/ci.yml`)

Runs on every push and pull request to `main`:

```yaml
Jobs:
  - security-scan:
      - Gitleaks secret scanning
      - Prevents accidental credential commits
  
  - test-and-build:
      - Python 3.11 setup
      - Dependency installation
      - Code compilation check (compileall)
      - Docker image build
      - Caching for faster builds
```

**Purpose**: Ensures code quality, security, and successful Docker builds before merging.

### **2. Gemini-Powered Automation** (`.github/workflows/gemini-*.yml`)

**Intelligent Code Reviews**:
- Automatically reviews PRs using Gemini 2.5 Flash
- Provides inline code suggestions with severity levels
- Checks for security issues, performance, and best practices

**Issue Triage**:
- Auto-labels new issues based on content
- Scheduled triage runs hourly
- Uses Gemini to categorize issues intelligently

**Commands**:
- Comment `@gemini-cli /review` on a PR for a detailed review
- Comment `@gemini-cli /triage` on an issue for label suggestions
- Comment `@gemini-cli <your request>` for general AI assistance

**Files**:
- `gemini-dispatch.yml` - Main orchestrator
- `gemini-review.yml` - PR review automation
- `gemini-triage.yml` - Issue labeling
- `gemini-scheduled-triage.yml` - Hourly issue triage
- `gemini-invoke.yml` - General-purpose AI assistant

---

## 🧠 **Prompt Engineering**

Detailed documentation of the system prompts, grounding strategies, and hallucination prevention techniques can be found in **[PROMPTS.md](PROMPTS.md)**.

**Key Strategies**:
- ✅ **Grounding First**: All responses cite NG12 guidelines
- ✅ **Tool Use**: Function Calling for dynamic patient data retrieval
- ✅ **Conservative Approach**: Clear refusal when evidence is insufficient
- ✅ **Structured Output**: Consistent formatting for assessments
- ✅ **Reusable Pipeline**: Shared RAG across both use cases

---

## 📁 **Project Structure**

```
ng12-cancer-assessor/
├── .env                          # Environment configuration (create from template)
├── .env.template                 # Environment template
├── .gitignore                    # Git ignore rules
├── Dockerfile                    # Docker build configuration
├── docker-compose.yml            # Multi-container orchestration
├── docker-start.sh               # Container startup script
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── PROMPTS.md                    # Prompt engineering documentation
├── ng12-service-account.json     # GCP credentials (NOT committed)
│
├── .github/                      # GitHub Actions CI/CD
│   ├── workflows/
│   │   ├── ci.yml                # Main CI/CD pipeline
│   │   ├── gemini-dispatch.yml  # AI automation orchestrator
│   │   ├── gemini-review.yml    # PR review automation
│   │   ├── gemini-triage.yml    # Issue triage
│   │   └── ...
│   └── commands/                 # Gemini CLI configurations
│
├── data/                         # Data directory
│   ├── patients.json             # Patient records (10 patients)
│   ├── ng12_guidelines.pdf       # Downloaded NG12 PDF
│   └── vector_store/             # ChromaDB persistent storage
│
├── src/                          # Source code
│   ├── main.py                   # FastAPI application entry point
│   ├── models.py                 # Pydantic data models
│   ├── assessment_engine.py      # Part 1: Clinical assessment logic
│   ├── chat_engine.py            # Part 2: Conversational AI
│   ├── rag_pipeline.py           # Shared RAG pipeline
│   ├── gemini_agent.py           # Gemini 2.5 Flash integration
│   ├── embedding_service.py      # Vertex AI embeddings
│   ├── vector_store.py           # ChromaDB wrapper
│   ├── pdf_parser.py             # NG12 PDF processing
│   └── patient_loader.py         # Patient data retrieval
│
├── scripts/                      # Utility scripts
│   └── initialize_vector_store.py # Vector DB initialization
│
├── frontend/                     # Web UI
│   └── index.html                # Single-page application
│
└── tests/                        # Test suite
    └── test_assessment_api.py    # Integration tests
```

---

## 🔧 **Troubleshooting**

### **Issue: "Google Cloud credentials not found"**

**Solution**:
1. Verify `ng12-service-account.json` exists in project root
2. Check `.env` file has correct path:
   ```bash
   GOOGLE_APPLICATION_CREDENTIALS=./ng12-service-account.json
   ```
3. For Docker, ensure volume mount is correct:
   ```bash
   -v $(pwd)/ng12-service-account.json:/app/credentials.json:ro
   ```

### **Issue: "Vector store not initialized"**

**Solution**:
```bash
# Run initialization script
python scripts/initialize_vector_store.py

# If using Docker, the script runs automatically on first start
docker compose up --build
```

### **Issue: "Port 8000 already in use"**

**Solution**:
```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9

# Or change the port in .env
API_PORT=8001
```

### **Issue: Mock mode activated automatically**

**Cause**: Vertex AI authentication failed, falling back to mock embeddings.

**Solution**:
1. Verify Vertex AI API is enabled in your GCP project
2. Check service account has `roles/aiplatform.user` role
3. Ensure `.env` has correct `GOOGLE_CLOUD_PROJECT`

---

## 📊 **Available Test Patients**

The system includes 10 pre-configured patients for testing:

| Patient ID | Age | Gender | Key Symptoms | Expected Assessment |
|-----------|-----|--------|--------------|-------------------|
| PT-101 | 55 | Male | Unexplained hemoptysis, fatigue | Urgent Referral |
| PT-102 | 25 | Female | Persistent cough, sore throat | No Action |
| PT-103 | 45 | Male | Persistent cough, SOB | Urgent Investigation |
| PT-104 | 35 | Female | Dysphagia | Urgent Investigation |
| PT-105 | 65 | Male | Iron-deficiency anaemia | Urgent Referral |
| PT-106 | 18 | Female | Fatigue | No Action |
| PT-107 | 48 | Male | Persistent hoarseness | Urgent Investigation |
| PT-108 | 32 | Female | Unexplained breast lump | Urgent Referral |
| PT-109 | 45 | Male | Dyspepsia | No Action |
| PT-110 | 60 | Male | Visible haematuria | Urgent Referral |

---

## 🎯 **Key Features**

### **Part 1 Highlights**
- ✅ **Function Calling**: Gemini agent uses tools to fetch patient data dynamically
- ✅ **RAG Grounding**: All assessments cite specific NG12 guideline sections
- ✅ **Risk Classification**: Categorizes into Urgent Referral/Investigation/No Action
- ✅ **Confidence Scoring**: Provides evidence-based confidence metrics

### **Part 2 Highlights**
- ✅ **Multi-turn Memory**: Maintains conversation context across sessions
- ✅ **Citation-backed**: Every claim includes NG12 page numbers and excerpts
- ✅ **Guardrails**: Refuses to answer when evidence is insufficient
- ✅ **Shared Pipeline**: Reuses same vector store and embeddings from Part 1

---

## 📚 **Additional Resources**

- **[PROMPTS.md](PROMPTS.md)** - Prompt engineering strategy and techniques
- **[Technical Assessment](Technical-Assessment.txt)** - Original requirements
- **[API Documentation](http://localhost:8000/docs)** - Interactive Swagger UI
- **[NICE NG12 Guidelines](https://www.nice.org.uk/guidance/ng12)** - Source guidelines

---

## 🤝 **Contributing**

This is a technical assessment submission. For production use:

1. Replace mock fallbacks with proper error handling
2. Implement comprehensive test suite
3. Add rate limiting and authentication
4. Configure CORS for production domains
5. Set up monitoring and logging infrastructure
6. Implement proper secrets management (e.g., Google Secret Manager)

---

## 📝 **License**

This project is submitted as part of a technical assessment for **C the Signs**.

---

## 🙏 **Acknowledgments**

- **NICE** for the NG12 Cancer Guidelines
- **Google Cloud** for Vertex AI platform
- **Anthropic** for Claude assistance in development
- **C the Signs** for the opportunity

---

**Last Updated**: January 7, 2026
