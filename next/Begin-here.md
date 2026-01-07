````markdown
# What‑Is‑It‑About: NG12 Cancer Risk Assessor & Conversational Clinical AI

## 📌 High‑Level Summary

This take‑home assessment is a **two‑part technical challenge** designed to evaluate your ability to build and orchestrate **LLM‑powered reasoning agents** that:

⚡ Combine **structured patient data** with **unstructured clinical guideline text**

⚡ Reuse a **single RAG (Retrieval‑Augmented Generation) pipeline** across:
- A **deterministic clinical decision support workflow (Part 1)**
- A **conversational, chat‑based interface (Part 2)**

**Estimated effort:** ~5–7 hours

**Core LLM platform (required):** Google Vertex AI — Gemini 1.5

**Service must be:** a Dockerized FastAPI application

## 🧾 Sources

1. Slack message with assessment prompt
2. Attached PDF (`Technical Assessment.pdf`)
3. Provided patient data schema
4. NG12 guideline PDF (download link included in the brief)

---

## 🧠 Part 1: “NG12 Cancer Risk Assessor”

### 🎯 Objective

Build a **clinical decision support agent** that:

1. Accepts a **Patient ID** via API
2. Retrieves structured patient data
3. Searches the **NICE NG12 cancer guideline PDF** using RAG
4. Outputs a **diagnostic risk assessment** (urgent referral / urgent investigation / none)
5. Includes **specific guideline citations** supporting the decision

---

## 📦 Required Components

### Backend

- FastAPI service wrapped in Docker
- Endpoints must include:
  - `POST /assess` (or similar) to evaluate risk for a given Patient ID

### Data Inputs

#### A. Structured Data
A JSON file (`patients.json`) simulating your BigQuery table with fields such as:

```json
[
  {
    "patient_id": "PT-101",
    "name": "John Doe",
    "age": 55,
    "gender": "Male",
    "smoking_history": "Current Smoker",
    "symptoms": ["unexplained hemoptysis","fatigue"],
    "symptom_duration_days": 14
  },
  {
    "patient_id": "PT-110",
    "name": "Bruce Wayne",
    "age": 60,
    "gender": "Male",
    "smoking_history": "Never Smoked",
    "symptoms": ["visible haematuria"],
    "symptom_duration_days": 2
  }
]
````

> ⚠️ Make sure the JSON is well‑formed and correctly parsed. The brief shows formatting anomalies.

#### B. Unstructured Data (Guideline)

* Download the full NG12 PDF:

  ```
  https://www.nice.org.uk/guidance/ng12/resources/suspected-cancer-recognition-and-referral-pdf-1837268071621
  ```
* Build a PDF parser to extract embeddings and section metadata.
* Store embeddings in a vector store (e.g., FAISS, ChromaDB).

---

## 🧠 RAG Pipeline Requirements

The same RAG pipeline must be used for:

1. Clinical decision support
2. Conversational agent (Part 2)

### RAG Setup

* Embed PDF text using **Vertex AI embeddings**
* Store in a vector DB with identifiers (page, chunk_id)
* Retrieval should return:

  * Relevant sections by similarity
  * Citation metadata (page, section IDs)

---

## 🔎 Output for Part 1

The API should return JSON like:

```json
{
  "patient_id": "PT-101",
  "assessment": "Urgent Referral",
  "reasoning": "Based on age and symptom combination with citations from NG12 sections X, Y",
  "citations": [
    {
      "source": "NG12 PDF",
      "page": 23,
      "chunk_id": "ng12_0023_01",
      "excerpt": "Text relevant to referral criteria..."
    }
  ]
}
```

---

## 🧾 Prompt Engineering (PROMPTS.md)

You must include a file explaining your system prompt strategy:

Examples to document:

* How system prompts enforce **grounded answers**
* How reasoning is structured for deterministic output
* How citations are requested from the LLM
* How hallucination is prevented

---

## 🎨 Minimal Frontend (Part 1)

A simple UI that:

* Takes a Patient ID
* Calls your API
* Displays:

  * Assessment
  * Reasoning
  * Citation excerpts

---

## 🧠 Part 2: Conversational AI Over NG12

### 🎯 Objective

Extend the solution to include a **chat interface** with RAG retrieval over the same NG12 vector store.

### Core Capabilities

Your chat interface must:

* Answer clinical guideline questions like:

  * “What symptoms trigger an urgent referral for lung cancer?”
  * “Does persistent hoarseness require urgent referral, and at what age?”
* Support **multi‑turn conversation**
* Return **grounded answers with citations**

---

## 🔌 Required API Endpoints (FastAPI)

### 1) `POST /chat`

Params:

```json
{
  "session_id": "string",
  "message": "string",
  "top_k": 5
}
```

Behavior:

* Retrieve relevant guideline text using vector search
* Combine with conversation history
* Return JSON like:

```json
{
  "session_id": "abc123",
  "answer": "Based on NG12, ...",
  "citations": [
    {
      "source": "NG12 PDF",
      "page": 45,
      "chunk_id": "ng12_0045_02",
      "excerpt": "Relevant excerpt..."
    }
  ]
}
```

---

### 2) `GET /chat/{session_id}/history`

(Optional but encouraged)

* Return stored conversation history

---

### 3) `DELETE /chat/{session_id}`

(Optional but encouraged)

* Clear conversation context

---

## 🧠 Conversation Memory Requirements

Memory:

* Acceptable: in‑memory store
* Optional: Redis / SQLite

Used for follow‑ups such as:

* “What about if the patient is under 40?”
* “Can you quote the part about duration thresholds?”

---

## 🛡️ Guardrails & Grounding

Your chat agent must:

✔ Only use retrieved evidence
✔ Refuse or qualify answers lacking evidence
✔ Always include citations
✔ Avoid invented criteria

---

## 📋 Evaluation Criteria (Explicit + Inferred)

### Part 1

| Category      | What Reviewers Expect            |
| ------------- | -------------------------------- |
| Correctness   | Accurate clinical decision logic |
| Grounding     | Uses NG12 text with citations    |
| Modularity    | Clear code structure             |
| Reliability   | RAG retrieval consistent         |
| Documentation | Clear README + PROMPTS.md        |

### Part 2

| Category             | Expected Behavior                   |
| -------------------- | ----------------------------------- |
| Groundedness         | Always supported by NG12 text       |
| Citation Quality     | Page, chunk IDs, relevant excerpts  |
| Multi‑turn Coherence | Handles context and follow‑ups      |
| Failure              | Clear “not found/unclear” responses |
| Pipeline Reuse       | No re‑embedding per chat request    |

---

## ❓ Known Ambiguities / Clarifications Needed

These details are **not explicitly specified** and you should clarify with the hiring team if possible:

### Data

* Are there additional structured fields expected (e.g., lab results)?
* Are symptom synonyms allowed or normalized? (E.g., hemoptysis = coughing up blood)

### RAG

* How large should chunks be (sentences, paragraphs)?

### Performance

* Are there latency/performance limits for endpoints?

### Deployment

* Should the solution be hosted publicly (e.g., Cloud Run) or is local Docker accepted?

---

## 🧾 Architecture Diagram (Example)

```
                       ┌───────────────────────────┐
 Patient ID → FastAPI │                           │
 (POST /assess)        │        API Server         │
                       │                           │
                       └─────────────▲─────────────┘
                                     │
                   ┌────────────────▼────────────────┐
                   │         RAG Pipeline              │
                   │ (Vector Search + Retrieval)       │
                   │   Vector DB (FAISS/ChromaDB)      │
                   └────────────────▲─────────────────┘
                                     │
       ┌──────────────┬──────────────┴──────────────┬──────────────┐
       │              │                             │              │
Structured Data   NG12 PDF Parsing & Embeddings  Gemini 1.5       Chat Logic
(patients.json)   (PDF → chunks → vectors)        (LLM)         (Multi‑turn Logic)
```

---

## 🛠️ Step‑by‑Step Plan

### 🚀 Phase 0: Setup

1. Create repo with LICENSE, README
2. Docker + Python environment
3. Install FastAPI, Vertex AI SDK, vector DB libraries

---

### 📌 Phase 1: Part 1 Implementation

1. Load `patients.json`
2. Write PDF parser → chunks + metadata
3. Build vector index (FAISS/Chroma)
4. Create `POST /assess`
5. Integrate Vertex embeddings + Gemini 1.5
6. Generate citations
7. Test endpoints locally
8. Build minimal UI page "Assess"

---

### 🧠 Phase 2: Prompt Engineering

1. Write PROMPTS.md

   * System prompt for clinical reasoning
   * Avoiding hallucinations
   * Citation formatting

---

### 💬 Phase 3: Part 2 - Chat

1. Add chat endpoints
2. Add conversation memory
3. Frontend: “Chat” tab
4. Citation UI
5. Multi‑turn logic
6. Failure behavior

---

### 🚢 Phase 4: Testing & Validation

1. Test edge cases
2. Ensure citations match PDF text
3. Session management
4. Docker test
5. Optional public demo

---

## 📌 Checklists

### Deliverables Checklist

* [ ] FastAPI backend
* [ ] Vector DB + embeddings
* [ ] RAG pipeline reused
* [ ] Dockerfile
* [ ] `PROMPTS.md`
* [ ] Chat mode endpoints
* [ ] Frontend UI
* [ ] Bidirectional communication
* [ ] README with running instructions

---

## 🧪 Example Tests

| Test                                | Expected                              |
| ----------------------------------- | ------------------------------------- |
| PT‑101                              | Urgent referral with correct sections |
| Ask chat: “dyspepsia investigation” | Grounded answer with citations        |
| Missing evidence                    | “Not found in NG12”                   |

---

## 🧩 Assumptions & Trade‑offs (to Document)

1. Using FAISS for speed vs cloud vector engine
2. In‑memory chat memory vs persistent store
3. Chunk sizes chosen for retrieval recall

---

## 📝 Prompt Engineering Examples

### System Prompt (Part 1)

```
You are a clinical decision agent. Use only the retrieved NG12 excerpts
to decide if the patient meets referral criteria. Cite page and chunk.
Do not hallucinate.
```

### System Prompt (Chat)

```
You are a clinical assistant grounded in NG12. Answer using only retrieved
evidence. If insufficient evidence, say “I cannot find support in NG12.”
Include product citations.
```

---

## 📦 How to Run Locally

```bash
docker build -t ng12-assessor .
docker run -p 8000:8000 ng12-assessor
```

Open browser → `localhost:8000`

---

## 🎯 Final Notes

This assessment tests **engineering rigour**, **architectural design**, **LLM grounding**, **documentation clarity**, and **careful prompt engineering**.

Focus not just on *making it work*, but *making it robust, well‑structured, and well‑justified*.

---

```

---

If you want, I can also generate a **pre‑populated repo structure** (with file templates like `main.py`, `Dockerfile`, `PROMPTS.md`, etc.) based on this doc. Just ask!
::contentReference[oaicite:0]{index=0}
```
