# FF AI Support Assistant Backend

Phase 1 builds the document-ingestion and semantic-search foundation. The backend uses FastAPI,
LangChain, LangGraph, and local persistent ChromaDB. Source documents live in the repository-level
`data/` folder.

## Planned flow

```text
data/ -> loaders -> splitter -> embeddings -> ChromaDB -> LangChain retriever -> LangGraph answer flow
```

Excel files use one row per chunk, with the column headers copied into each row chunk and the
workbook/sheet/row stored as metadata. PDFs use hybrid chunking: preserve headings, procedures,
and tables first, then split long narrative sections by token size. This prevents a troubleshooting
step or table row from being separated from the context needed to understand it.

PowerPoint files will be indexed slide by slide. Each slide chunk preserves the slide number,
title, body text, and table text as metadata so answers can cite the correct slide.

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