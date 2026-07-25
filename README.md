# 🚀 CareerPilot AI

**Autonomous Multi-Agent Placement Preparation Platform**

CareerPilot AI is an AI-powered career preparation platform that uses multiple specialized agents orchestrated through LangGraph to help students and professionals prepare for tech placements. It features resume analysis, company research with live web search, mock interviews, coding assistance, personalized study roadmaps, and document-grounded Q&A through RAG.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **Resume Analyzer** | Upload PDF resumes for ATS scoring, gap analysis, and improvement suggestions |
| 🏢 **Company Research** | Live web search to research hiring processes, interview rounds, and preparation tips |
| 🎤 **Interview Coach** | Interactive HR and technical mock interviews with scoring and feedback |
| 💻 **Coding Assistant** | Code review, bug detection, complexity analysis, and optimization suggestions |
| 🗺️ **Roadmap Planner** | Personalized week-by-week placement preparation plans |
| 📚 **PDF / RAG Chat** | Upload documents and ask questions with citation-backed answers |
| 📊 **Analytics** | Track preparation progress and agent usage |
| 🧠 **Memory** | SQLite-backed conversation history that persists across sessions |

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Streamlit Frontend                      │
│  Dashboard │ Chat │ Resume │ Company │ Interview │ ...    │
└──────────────────┬───────────────────────────────────────┘
                   │ HTTP (REST)
┌──────────────────▼───────────────────────────────────────┐
│                  FastAPI Backend                          │
│  /health │ /chat │ /documents │ /rag/status               │
└──────────────────┬───────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────┐
│            LangGraph Planner (StateGraph)                 │
│                                                           │
│  User Query → [Classify] → Conditional Route              │
│                    ↓                                      │
│  ┌─────────┬───────────┬───────────┬──────────┬────────┐ │
│  │ Resume  │ Company   │ Interview │ Coding   │Roadmap │ │
│  │ Agent   │ Agent     │ Agent     │ Agent    │Agent   │ │
│  │         │ +Web      │ +Scoring  │ +BigO    │+Plans  │ │
│  │         │  Search   │           │          │        │ │
│  └─────────┴───────────┴───────────┴──────────┴────────┘ │
│                         ↕                                 │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ RAG Pipeline: ChromaDB + SentenceTransformers        │ │
│  │ Memory: SQLite Checkpoint Store                      │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Google Gemini / Groq (LLaMA) |
| Orchestration | LangGraph StateGraph |
| Framework | LangChain |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Vector DB | ChromaDB |
| Embeddings | SentenceTransformers (all-MiniLM-L6-v2) |
| Database | SQLite (WAL mode) |
| Web Search | DuckDuckGo |
| PDF Parsing | PyPDF |

## 📦 Project Structure

```
careerpilot/
├── backend/
│   ├── agents/
│   │   ├── planner.py      # LangGraph orchestrator with conditional routing
│   │   ├── common.py       # Shared state and specialist runner
│   │   ├── resume.py       # Resume analysis agent
│   │   ├── company.py      # Company research + web search agent
│   │   ├── interview.py    # Mock interview agent
│   │   ├── coding.py       # Code review agent
│   │   ├── roadmap.py      # Study plan agent
│   │   └── rag.py          # RAG-grounded Q&A agent
│   ├── rag/
│   │   ├── service.py      # High-level RAG orchestration
│   │   ├── repository.py   # SQLite document registry
│   │   ├── embedding.py    # SentenceTransformer adapter
│   │   ├── loader.py       # PDF document loader
│   │   ├── retriever.py    # Retriever factory
│   │   └── splitter.py     # Text chunking
│   ├── tools/
│   │   └── search.py       # DuckDuckGo web search
│   ├── memory/
│   │   └── checkpoint.py   # SQLite conversation history
│   ├── config.py           # Pydantic settings
│   ├── llm.py              # LLM provider abstraction
│   └── main.py             # FastAPI application
├── frontend/
│   └── streamlit_app.py    # Streamlit UI
├── database/               # Auto-created: SQLite + ChromaDB storage
└── ...
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- A Gemini API key (or Groq API key)

### 1. Clone & Install

```bash
git clone https://github.com/Darshi7587/CareerPilot-.git
cd CareerPilot-

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example and fill in your API keys
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY (or GROQ_API_KEY)
```

### 3. Start the Backend

```bash
python -m uvicorn careerpilot.backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Start the Frontend

```bash
streamlit run careerpilot/frontend/streamlit_app.py
```

### 5. Open in Browser

Navigate to `http://localhost:8501` — you should see the CareerPilot dashboard!

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_LLM_PROVIDER` | `gemini` | LLM provider: `gemini` or `groq` |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GROQ_API_KEY` | — | Groq API key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name |
| `CAREERPILOT_SQLITE_PATH` | `careerpilot/backend/database/careerpilot.sqlite3` | SQLite DB path |
| `CAREERPILOT_CHROMA_PATH` | `careerpilot/backend/database/chroma` | ChromaDB storage path |
| `CAREERPILOT_CHECKPOINT_PATH` | `careerpilot/backend/memory/checkpoints.sqlite3` | Conversation history DB |
| `CAREERPILOT_UPLOAD_PATH` | `careerpilot/backend/database/uploads` | PDF upload directory |
| `CAREERPILOT_RAG_CHUNK_SIZE` | `1000` | Text chunk size for RAG |
| `CAREERPILOT_RAG_CHUNK_OVERLAP` | `150` | Chunk overlap for RAG |
| `CAREERPILOT_RAG_TOP_K` | `4` | Number of chunks to retrieve |
| `CAREERPILOT_MAX_UPLOAD_BYTES` | `10485760` | Max upload size (10 MB) |
| `CAREERPILOT_HISTORY_LIMIT` | `8` | Conversation history depth |
| `DUCKDUCKGO_MAX_RESULTS` | `5` | Web search results count |
| `APP_NAME` | `CareerPilot AI` | Application display name |
| `CAREERPILOT_BACKEND_URL` | `http://127.0.0.1:8000` | Backend API URL |

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Send message to planner |
| `GET` | `/documents` | List uploaded documents |
| `POST` | `/documents` | Upload PDFs |
| `POST` | `/documents/{id}/reindex` | Reindex a document |
| `DELETE` | `/documents/{id}` | Delete a document |
| `GET` | `/rag/status` | RAG index status |

## 🧪 Testing

```bash
python -m pytest tests/ -v
```


