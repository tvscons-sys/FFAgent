# FF AI Support Assistant Backend

Phase 1 builds the document-ingestion and semantic-search foundation. The backend uses FastAPI,
LangChain, LangGraph, and Qdrant. Source documents live in the repository-level `data/` folder.

## Planned flow

```text
data/ -> loaders -> splitter -> embeddings -> Qdrant -> LangChain retriever -> LangGraph answer flow
```

The ingestion route is currently a placeholder. Implement the pipeline modules in `app/rag/`
before connecting the Android `/chat` request.

## Local setup

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET http://127.0.0.1:8000/health`