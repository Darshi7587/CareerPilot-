# CareerPilot AI

CareerPilot AI is a placement-preparation platform built as a modular LangGraph application.

## Current status

- Project scaffold created
- Python environment configured
- Core dependencies installed
- Planner Agent implemented with conditional routing
- SQLite-backed checkpoint helper added

## Folder layout

- `careerpilot/backend/agents` - planner and future specialized agents
- `careerpilot/backend/rag` - document loading and retrieval pipeline
- `careerpilot/backend/tools` - web search and other reusable tools
- `careerpilot/backend/memory` - SQLite persistence helpers
- `careerpilot/backend/database` - local database storage
- `careerpilot/frontend` - Streamlit MVP now, React later

## Run the backend

```bash
python -m uvicorn careerpilot.backend.main:app --reload
```

## Run the Streamlit MVP

```bash
streamlit run careerpilot/frontend/streamlit_app.py
```

## Next module

The next step is to replace the planner stubs with the Resume Analyzer Agent.
