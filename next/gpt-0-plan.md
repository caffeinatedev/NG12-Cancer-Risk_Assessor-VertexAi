Here’s a **clear breakdown of what your `what‑is‑it‑about.md` most likely *doesn’t* include yet** and what you need to get you started immediately — based on the screenshots you shared of the Slack message and the partial PDF.

I’m not pulling extra proprietary content from the PDF — I’m extracting what’s visible and mapping that into a detailed **starter plan**.

---

## ✅ **1. What the Assessment *Actually Is***

From the Slack message snippet:

* It’s a **take‑home technical assessment** due **January 7, 2026**.
* It is designed to take **~5–7 hours.**
* It focuses on building a **reasoning agent** that:

  * Combines **structured patient data** with **unstructured clinical guidelines**.
  * Reuses a **single RAG (retrieval‑augmented generation) pipeline** across:

    * A **clinical decision support workflow**.
    * A **conversational chat‑based interface**.
* You’ll find *full* instructions in the attached challenge brief.
  (Your MD file may only have a summary — not all details.)

This means the *core goal* is **architecture, reasoning design, grounding, tooling** — not just a UI.
The reviewers care how *you* design and justify your solution.

**Missing from many summaries:**
✔ What the assessment *is about* (this should be expanded)
✔ Emphasis on RAG pipeline reuse
✔ Dual workflows — clinical and chat interface
✔ Time estimate (5–7 hrs)

---

## ✅ **2. Deliverables You Need to Clarify**

Your minimal `what‑is‑it‑about.md` likely does *not* yet list these clearly:

**Final deliverables:**

1. **Code repository** (public or private invite)
2. **Implementation of the reasoning agent**

   * a clinical decision support workflow
   * a conversational/chat interface
3. **RAG pipeline reused between both modes**
4. **Readme / documentation**

   * How to run the project
   * Architecture diagram
   * Assumptions and trade‑offs
5. **Brief notes to reviewers**

   * What you would improve with more time
   * Why you chose this approach

**Checklist to add if missing:**

* Deployment instructions
* Test cases or demonstration scripts
* Data samples (if any synthetic data used)

---

## ✅ **3. Technical Stack Considerations**

The partial PDF shows something like:

> *Build a Clinical Decision Support Agent using **Google Vertex AI (Gemini 1.5)**…*

So the stack likely expected (but your MD may miss):

📌 **Core ML/LLM Infrastructure**

* **Google Vertex AI** (Gemini 1.5 ‑ mentioned in the PDF screenshot)
* RAG setup (vector store + Retriever + LLM)
* Embeddings (Vertex AI or alternative)

📌 **Backend**

* Python/Node.js or similar language
* Web framework (FastAPI, Flask, Next.js API routes)

📌 **Front‑end**

* Chat‑based interface (React/Next.js/Vue)
* Simple UI to query the agent

📌 **Data**

* Structured patient data (CSV/JSON)
* Unstructured clinical guidelines (e.g., NICE NG12 national suspected cancer guideline)
  NICE NG12 is the reputed clinical guideline used for suspected cancer referrals. It contains symptom/criteria logic for decision rules — exactly what your *clinical decision workflow* needs to reason over. ([Cancer Research UK][1])

📌 **Vector Store**

* Pinecone / Milvus / Weaviate / Vertex AI Matching Engine

📌 **Testing**

* Unit tests for pipeline
* Integration test for chat agent

**Your MD may not yet call out:**

* Stack specifics (Vertex, vector store choices, frontend tech)
* Dependencies and versions
* Deployment considerations

---

## ✅ **4. Requirements & Criteria for “Passing”**

Your current MD probably *doesn’t* include any grading criteria, because **none is stated explicitly in the Slack text** — but you can *infer* what reviewers will judge.

### **What reviewers care about**

✔ **Correctness of the reasoning agent**
✔ **Quality of the architecture**
✔ **Reusability of the RAG pipeline**
✔ **Cleanliness & readability of code**
✔ **Documentation & justification of design choices**
✔ **Trade‑offs, assumptions, and future improvements**
✔ **Minimal working UX**

### **Likely implicit grading rubric**

| Category      | What to include                           |
| ------------- | ----------------------------------------- |
| Functionality | Working RAG agent with both UIs           |
| Design        | Clear modular architecture                |
| Grounding     | RAG retrieves real guideline text         |
| Reasoning     | Correct clinical decisions for test cases |
| Tooling       | Use of Vertex AI (if specified)           |
| Documentation | Clear README + rationale                  |
| Quality       | Testing, structure, code quality          |

---

## ✅ **5. Ambiguities Your MD Should Resolve**

Your current summary might *not yet address*:

❓ Are you expected to host it (Vercel/Cloud Run)?
❓ Does the pipeline need to connect to a real medical dataset?
❓ What format should patient structured data be?
❓ How do we simulate NICE guideline logic?
❓ How thorough is the chat interface?
❓ How to score answers clinically?

You should draft clarifying questions for the hiring team *before coding* — e.g., data format expectations, scoring rubric, allowed libraries.

---

## ✅ **6. First Immediate Action Plan**

Below is a **step‑by‑step actionable plan** you can start *today*:

---

### **Step 1 — Fully read the attached PDF**

You must extract:
✔ Full requirements
✔ Part 1 / Part 2 descriptions
✔ Input/Output expectations
✔ Example cases

If you can’t OCR/read the PDF automatically, upload it to an LLM and ask it to extract sections.

---

### **Step 2 — Define Requirements in Your MD**

Add these headings:

```
## Objective
## Deliverables
## Technical Stack
## Input & Output Expectations
## Success Criteria
## Assumptions
```

Populate with what you learned.

---

### **Step 3 — Research Clinical Guideline**

* Download NICE NG12 suspected cancer guideline
* Identify decision rules (symptoms → referrals)
  (You can cite free NICE summary as reference.) ([Cancer Research UK][1])

This will become your ground truth for the clinical workflow.

---

### **Step 4 — Design Architecture**

Create a diagram showing:

```
Patient Data --\
                Vector Embedder → Vector Store → Retriever ↔ LLM
Clinical Text --/
                                  ↘ Conversational UI
                                  ↘ Clinical Decision API
```

Document each component.

---

### **Step 5 — Pick Tools**

Decide concretely:

| Component     | Choice                            |
| ------------- | --------------------------------- |
| LLM           | Vertex Gemini 1.5                 |
| Embeddings    | Vertex Embeddings                 |
| Vector Store  | Vertex Matching Engine / Pinecone |
| Backend       | FastAPI (Python)                  |
| Frontend      | Next.js (React)                   |
| Hosting       | Google Cloud                      |
| Docs & Readme | Markdown in repo                  |

---

### **Step 6 — Build a Minimal Viable Version**

Deliver first:

✔ RAG pipeline
✔ Simple conversational frontend
✔ Simple clinical decision API returning structured output

Test with synthetic data.

---

### **Step 7 — Write Tests**

Cover:

* RAG retrieval
* Decision logic (NG12 rules)
* Chat intents

---

### **Step 8 — Finalize Documentation**

In repo:

```
README.md
ARCHITECTURE.md
ASSUMPTIONS_AND_TRADEOFFS.md
RUN_INSTRUCTIONS.md
```

---

## 🧠 Summary of What Your MD Needs to Add

If any of these are *missing*, add:

✅ Full deliverables list
✅ Stack choices
✅ Expected I/O formats
✅ Inline success criteria
✅ Example tests
✅ Deployment instructions
✅ Trade‑offs and assumptions
✅ Clarifying questions

---

If you want, **paste the current contents of your what‑is‑it‑about.md** and I can mark exactly what lines to add or revise.

[1]: https://www.cancerresearchuk.org/health-professional/diagnosis/primary-care/suspected-cancer-referral-guidelines/nice-ng12?utm_source=chatgpt.com "NICE (NG12) Suspected Cancer: Recognition & Referral ..."
