# Required Deliverables & Specifications

This document outlines the complete set of requirements, deliverables, and specifications for the NG12 Cancer Risk Assessor project, as derived from the Technical Assessment provided.

## Part 1: The "NG12 Cancer Risk Assessor"

### 1. Objective
Build a Clinical Decision Support Agent using **Google Vertex AI (Gemini 1.5)**.
*   **Input:** Patient ID.
*   **Process:** Retrieve patient records, consult Official NICE NG12 Cancer Guidelines (PDF).
*   **Output:** Risk assessment with citations ("Urgent Referral" or "Urgent Investigation").

### 2. Architecture
*   **Service:** FastAPI service wrapped in Docker.
*   **Logic Flow:**
    1.  **User Input:** Receive Patient ID via API.
    2.  **Tool Use (Data Retrieval):** Fetch structured data (Age, Symptoms) from `patients.json` (simulated DB).
    3.  **RAG (Guideline Lookup):** Search Vector Store for relevant NG12 PDF sections based on symptoms.
    4.  **Reasoning:** Synthesize data to determine if criteria are met.
    5.  **Output:** Return JSON with assessment and specific guideline citations.

### 3. Data Package
*   **Structured Data:** `patients.json` (provided in assessment text).
*   **Unstructured Data:** NICE NG12 Guidelines PDF (download from provided URL).
    *   *Instruction:* Build a pipeline to parse PDF, create embeddings (Vertex AI), and store in local Vector DB (ChromaDB/FAISS).

### 4. Deliverables (Part 1)
*   [ ] **Source Code (Modular Python):**
    *   PDF Ingestion Script (Parse PDF, build vector index).
    *   Agent Logic (Reasoning engine using Gemini 1.5).
    *   Tooling (Function calling to retrieve patient data).
*   [ ] **Prompt Engineering:** `PROMPTS.md` explaining System Prompt strategy.
*   [ ] **Dockerfile:** Working configuration to build the service.
*   [ ] **UI:** Minimal frontend to input Patient ID and view result.

---

## Part 2: Conversational AI (Chat Mode)

### 1. Objective
Extend solution with a conversational agent using the **same NG12 PDF content** and **same vector database** from Part 1.

### 2. Core Capabilities
*   Answer questions like:
    *   "What symptoms trigger an urgent referral for lung cancer?"
    *   "Does persistent hoarseness require urgent referral, and at what age?"
*   **Must:**
    1.  Retrieve relevant chunks from existing vector store.
    2.  Answer in natural language using *only* retrieved evidence.
    3.  Cite specific guideline source passages (page/section identifiers).

### 3. Requirements
*   **API Endpoints:**
    *   `POST /chat`:
        *   Input: `session_id`, `message`, `top_k` (optional).
        *   Behavior: Perform RAG, return grounded answer with citations.
    *   `GET /chat/{session_id}/history` (Optional but encouraged).
    *   `DELETE /chat/{session_id}` (Optional but encouraged).
*   **Conversation Memory:** In-memory or lightweight store (SQLite/Redis) to support follow-ups.
*   **Grounding & Guardrails:**
    *   Refuse/qualify answers if evidence is insufficient.
    *   Avoid inventing thresholds.
    *   Always include citations.
*   **UX:** Chat tab with message window, input box, and readable citations.

### 4. Deliverables (Part 2)
*   [ ] **CHAT_PROMPTS.md** (or extended `PROMPTS.md`): Chat system prompt and grounding strategy.
*   [ ] **UI Components:** Additional UI for chat experience.
*   [ ] **README Section:** How to run chat mode locally and in Docker.

---

## Evaluation Criteria
*   **Groundedness:** Answers supported by retrieved text.
*   **Citation Quality:** Specific and relevant passages.
*   **Multi-turn Coherence:** Handles follow-ups/context.
*   **Failure Behavior:** Appropriately says "not found" when evidence is missing.
*   **Reuse of Pipeline:** Uses same vector DB/ingestion as Part 1 (no re-downloading per request).
