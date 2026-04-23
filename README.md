# 🌶️ Chilli Internal Knowledge Base Q&A

> A Claude-powered RAG (Retrieval-Augmented Generation) tool that lets employees ask natural-language questions about company policies, HR documents, and process guides — and get instant, cited answers.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Claude AI answers** | Uses Claude (claude-sonnet-4-5 by default) with a strict RAG prompt |
| **Streaming responses** | Token-by-token streaming for instant feedback |
| **Multi-turn chat** | Maintains last 6 turns of conversation context |
| **FAISS vector search** | Semantic search over 20 HR/policy documents |
| **FAISS index persistence** | Index saved to disk — no rebuild on restart |
| **Source citations** | Every answer cites the exact document(s) it used |
| **Premium dark UI** | Inter font, glassmorphism cards, animated chat bubbles |
| **Suggested questions** | Quick-start prompts for new users |
| **Error handling** | Clear messages for bad API key, rate limits, missing docs |

---

## 🚀 Quick Start (Local)

### 1. Clone & create virtual environment
```bash
git clone <repo-url>
cd Chilli_Assignment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Generate sample documents
```bash
python create_sample_docs.py
```
This creates 20 realistic Word documents in `sample_docs/` covering:
Annual leave · Sick leave · Remote work · Code of conduct · Onboarding · Performance reviews · Compensation · IT security · Expenses · Recruitment · L&D · Probation · Offboarding · Data privacy · Health & safety · Travel · Communications · Promotions · Disciplinary · Company overview

### 4. Set your API key (optional — can also enter in the sidebar)
```bash
# Windows
set ANTHROPIC_API_KEY=sk-ant-...

# macOS/Linux
export ANTHROPIC_API_KEY=sk-ant-...
```

### 5. Run the app
```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                    │
│   Chat UI · Suggested Qs · Source Expander · Stats      │
└──────────────────────┬──────────────────────────────────┘
                       │ user query
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  RAG Retrieval Layer                     │
│  sentence-transformers/all-MiniLM-L6-v2 (local embed)   │
│  FAISS vector store (persisted to faiss_index/)          │
│  Top-K semantic search (default k=5)                     │
└──────────────────────┬──────────────────────────────────┘
                       │ ranked context chunks
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   Claude Generation                      │
│  System prompt with strict RAG grounding                │
│  Rolling 6-turn conversation history                    │
│  Streaming token output via Anthropic SDK               │
└─────────────────────────────────────────────────────────┘
```

**Stack:**
- **Frontend:** Streamlit + custom CSS (dark mode, glassmorphism)
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` — runs fully locally, no extra API cost
- **Vector DB:** FAISS (CPU) — persisted to `faiss_index/`
- **LLM:** Anthropic Claude (claude-sonnet-4-5 default)
- **Document parsing:** `docx2txt` + LangChain `DirectoryLoader`

---

## 🔄 Keeping the Knowledge Base Current

> As documents change, the system must stay in sync. Here's how I'd productionize this:

**Automated sync pipeline:**
1. **Document Watcher** — Monitor the `sample_docs/` folder (or SharePoint/Google Drive via API) for file change events using `watchdog` or a scheduled cron job.
2. **Diff-based reindexing** — When a file changes, delete only the FAISS vectors associated with that file's chunks (by filtering on `metadata.source`), re-parse the updated file, and upsert new vectors. This avoids full re-indexing on every change.
3. **Version tagging** — Store a `doc_versions.json` manifest mapping each file to its last-modified timestamp and checksum (MD5). On startup, compare against the live filesystem and trigger partial re-index only for changed files.
4. **Human-in-the-loop review** — For policy documents, require HR to mark a document as "published" before it enters the index (prevents drafts from being surfaced).
5. **Scheduled full rebuild** — Weekly full rebuild as a safety net to catch any drift.

**In production:** replace FAISS with a managed vector DB (Pinecone, Weaviate, pgvector) that supports real-time upserts and deletions with metadata filtering.

---

## 📁 Project Structure

```
Chilli_Assignment/
├── app.py                  # Main Streamlit app
├── create_sample_docs.py   # Generate 20 sample Word docs
├── requirements.txt
├── README.md
├── sample_docs/            # 20 HR/policy Word documents
│   ├── 01_annual_leave_policy.docx
│   ├── 02_sick_leave_policy.docx
│   └── ... (20 files)
└── faiss_index/            # Auto-created on first run
    ├── index.faiss
    └── index.pkl
```

---

## 📝 Sample Questions to Try

- *"How many annual leave days do I get?"*
- *"Can I work from home every day?"*
- *"What is the expense claim limit before I need pre-approval?"*
- *"How does the promotion process work?"*
- *"What should I do if I suspect a data breach?"*
- *"What's the notice period if I resign?"*

---

*Built as a Stage 2 take-home assignment — demonstrating Claude-powered RAG for internal HR knowledge management.*
