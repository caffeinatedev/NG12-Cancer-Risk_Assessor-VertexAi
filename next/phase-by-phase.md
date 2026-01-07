# Phase-by-Phase Implementation Plan: NG12 Cancer Risk Assessor

**Deadline:** January 7, 2026 | **Estimated Time:** 5-7 hours

## Task Overview

Build a two-part LLM-powered clinical reasoning agent:
- **Part 1:** Clinical decision support (risk assessment)
- **Part 2:** Conversational chat interface
- **Core Requirement:** Single RAG pipeline reused for both parts

**Tech Stack:** FastAPI + Docker + Vertex AI (Gemini 1.5) + ChromaDB/FAISS

---

## PHASE 0: Project Setup (30 mins)

### Actions:
1. Create project structure
2. Initialize git repository
3. Set up Python virtual environment
4. Install dependencies:
   - `fastapi`, `uvicorn`, `python-dotenv`
   - `google-cloud-aiplatform`
   - `chromadb` or `faiss-cpu`
   - `pypdf2` or `pdfplumber`
5. Create `.env.template` for Vertex AI credentials
6. Create `requirements.txt`
7. Initialize `README.md`

**Deliverable:** Working dev environment

---

## PHASE 1: Data Preparation (45 mins)

### Part A: Structured Data
1. Create `data/patients.json` with 10 patients
2. Validate JSON structure
3. Create `src/data_loader.py` for patient retrieval

### Part B: Unstructured Data
1. Download NG12 PDF: `https://www.nice.org.uk/guidance/ng12/resources/suspected-cancer-recognition-and-referral-pdf-1837268071621`
2. Save to `data/NG12_guideline.pdf`
3. Create `src/pdf_parser.py`:
   - Extract text with page numbers
   - Chunk into semantic sections
   - Preserve metadata

**Deliverable:** `patients.json` + NG12 PDF + parser

---

## PHASE 2: Build RAG Pipeline (90 mins)

### Actions:
1. **Create `src/embeddings.py`:**
   - Initialize Vertex AI embeddings
   - Embed text chunks

2. **Create `src/vector_store.py`:**
   - Initialize ChromaDB/FAISS
   - Store embeddings with metadata (page, chunk_id, excerpt)
   - Implement similarity search

3. **Create `scripts/build_index.py`:**
   - Parse PDF → chunks → embeddings → index
   - Persist vector store

4. Test retrieval with queries like "hemoptysis urgent referral"

**Deliverable:** Working vector store with NG12 embeddings

---

## PHASE 3: Part 1 - Clinical Decision Agent (120 mins)

### Part A: Agent Logic
1. **Create `src/agent.py`:**
   - Initialize Gemini 1.5
   - System prompt for clinical reasoning
   - Function calling for patient data

2. **Create `src/assessment_engine.py`:**
   - Orchestrate: Get patient → Query symptoms → RAG → Reasoning
   - Format output with citations

### Part B: API
1. **Create `src/main.py` (FastAPI):**
   - `POST /assess` → `{"patient_id": "PT-101"}`
   - Response: `{"patient_id", "assessment", "reasoning", "citations": [...]}`
   - `GET /health`

2. Test with all 10 patients

### Part C: Frontend
1. Create `frontend/index.html`:
   - Input form for Patient ID
   - Display assessment + reasoning + citations

**Deliverable:** Working assessment API + UI

---

## PHASE 4: Part 2 - Conversational Chat (90 mins)

### Part A: Chat Backend
1. **Create `src/chat_engine.py`:**
   - Session management (in-memory dict)
   - Conversation history storage

2. **Create `src/chat_agent.py`:**
   - Chat system prompt with guardrails
   - RAG retrieval + context-aware responses

3. **Add endpoints to `src/main.py`:**
   - `POST /chat` → `{"session_id", "message", "top_k"}`
   - `GET /chat/{session_id}/history`
   - `DELETE /chat/{session_id}`

### Part B: Chat Frontend
1. Create `frontend/chat.html`:
   - Chat window + input box
   - Display citations

**Deliverable:** Working chat with multi-turn context

---

## PHASE 5: Prompt Engineering Docs (30 mins)

### Actions:
1. **Create `PROMPTS.md`:**
   - Part 1 system prompt
   - Grounding enforcement strategy
   - Citation format instructions
   - Hallucination prevention

2. **(Optional) `CHAT_PROMPTS.md`:**
   - Chat-specific prompts
   - Multi-turn handling
   - Failure behavior

**Deliverable:** Documented prompt strategies

---

## PHASE 6: Dockerization (45 mins)

### Actions:
1. Create `Dockerfile`:
   - Python 3.11 base
   - Install dependencies
   - Copy source
   - Expose port 8000
   - CMD: `uvicorn src.main:app --host 0.0.0.0 --port 8000`

2. Create `.dockerignore`
3. Test: `docker build -t ng12-assessor .`
4. Test: `docker run -p 8000:8000 ng12-assessor`
5. Document in README

**Deliverable:** Working Docker container

---

## PHASE 7: Testing & Validation (45 mins)

### Test Cases:
1. **Assessment API:**
   - All 10 patients
   - Verify citations match PDF
   - Invalid patient ID

2. **Chat API:**
   - Questions with clear evidence
   - Questions with no evidence (should refuse)
   - Multi-turn follow-ups
   - Session management

3. **Edge Cases:**
   - Empty messages
   - Malformed requests

**Deliverable:** Validated system

---

## PHASE 8: Documentation (30 mins)

### Actions:
1. **Complete `README.md`:**
   - Overview + architecture diagram
   - Local setup instructions
   - Docker instructions
   - API documentation
   - Example requests/responses

2. **Create supplementary docs:**
   - `ASSUMPTIONS.md`: Chunk sizes, vector store choice
   - `TRADE_OFFS.md`: Speed vs accuracy, local vs cloud
   - `IMPROVEMENTS.md`: Production considerations

**Deliverable:** Professional documentation

---

## PHASE 9: Submission (15 mins)

### Actions:
1. Final code review
2. Push to GitHub
3. Test fresh clone and run
4. Prepare submission notes (assumptions, trade-offs, improvements)
5. Reply to Slack with GitHub link

---

## Recommended Timeline

**Day 1 (3-4 hours):**
- Phase 0: Setup (30m)
- Phase 1: Data Prep (45m)
- Phase 2: RAG Pipeline (90m)
- Phase 3: Part 1 start (60m)

**Day 2 (3-4 hours):**
- Phase 3: Part 1 complete (60m)
- Phase 4: Part 2 Chat (90m)
- Phase 5: Prompts (30m)
- Phase 6: Docker (45m)
- Phase 7: Testing (45m)
- Phase 8: Docs (30m)
- Phase 9: Submit (15m)

---

## Success Criteria

✅ **Grounding:** All answers cite specific PDF passages  
✅ **Reusability:** Single RAG pipeline for both workflows  
✅ **Documentation:** Clear PROMPTS.md + README  
✅ **Testing:** Edge cases and "no evidence" scenarios  
✅ **Modularity:** Clean code separation

---

## Project Structure

```
project/
├── data/
│   ├── patients.json
│   └── NG12_guideline.pdf
├── src/
│   ├── main.py              # FastAPI app
│   ├── agent.py             # Gemini 1.5 agent
│   ├── assessment_engine.py # Part 1 logic
│   ├── chat_engine.py       # Part 2 logic
│   ├── chat_agent.py        # Chat-specific agent
│   ├── embeddings.py        # Vertex AI embeddings
│   ├── vector_store.py      # ChromaDB/FAISS
│   ├── pdf_parser.py        # PDF processing
│   └── data_loader.py       # Patient data retrieval
├── scripts/
│   └── build_index.py       # Build vector index
├── frontend/
│   ├── index.html           # Assessment UI
│   └── chat.html            # Chat UI
├── Dockerfile
├── requirements.txt
├── .env.template
├── README.md
├── PROMPTS.md
└── ASSUMPTIONS.md
```
