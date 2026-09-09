# FF AI Support Assistant

FF AI Support Assistant is a hybrid support-assistant proof of concept for Flying Flea vehicle support. It combines a FastAPI backend, document-grounded RAG answers, a reusable Android SDK, a sample Android app, and an internal operations dashboard.

The POC supports:

- Customer questions through Android chat
- Exact, cached FAQ answers for approved common questions
- Semantic search over support documents using ChromaDB
- Grounded answer generation using Gemini
- Conversation persistence on the Android device
- Manual and chat-generated support tickets
- Resolution feedback and a 1-5 rating flow
- SQLite storage for chat metrics and tickets
- A browser-based admin dashboard

## Architecture

```text
Android sample app
        |
        v
Reusable Android SDK
        |
        | POST /chat
        | POST /tickets
        v
FastAPI backend
   |              |
   |              +--> SQLite metrics and tickets
   |
   +--> Exact FAQ layer
   |
   +--> ChromaDB semantic retrieval
             |
             +--> Support files in data/
             |
             +--> Gemini grounded answer generation

Admin dashboard --> GET /admin/metrics
```

## Repository Structure

```text
FFAgent/
├── backend/
│   ├── app/
│   │   ├── api/routes/       FastAPI endpoints
│   │   ├── core/              Configuration and SQLite metrics
│   │   ├── rag/               Loading, chunking, embeddings, retrieval, FAQ, generation
│   │   └── schemas/           API request and response models
│   ├── scripts/               Ingestion, search, and answer utilities
│   ├── storage/               ChromaDB and SQLite runtime data
│   ├── tests/                 Backend tests
│   ├── .env.example           Backend configuration template
│   └── requirements.txt       Python dependencies
├── android-sdk/
│   ├── ff-assistant-sdk/      Reusable Android support-chat SDK
│   ├── sample-app/            Demo app using the SDK
│   └── gradlew.bat            Gradle wrapper for Windows
├── dashboard/                 Static admin dashboard
└── data/                      Source support documents
```

## Requirements

- Windows PowerShell
- Python 3.11 or another supported Python environment
- Java 17
- Android Studio or Android SDK command-line tools
- An Android device or emulator
- A Gemini API key for generated RAG answers
- Network access between the Android device and the development computer

A physical Android phone and the development computer must be on the same network.

## Backend Setup

Open PowerShell and move to the backend directory:

```powershell
Set-Location "C:\Users\ThreshikaVij_5jgvhlh\OneDrive - RayReach Technologies Pvt. Ltd\Documents\FFAgent\backend"
```

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create the environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and set the Gemini key:

```env
GOOGLE_API_KEY=your_gemini_api_key
```

Important defaults include:

```env
PORT=8000
DATA_DIR=../data
CHROMA_PERSIST_DIRECTORY=./storage/chroma
CHROMA_COLLECTION=ff_support_documents
HF_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
GEMINI_MODEL=gemini-2.0-flash
RETRIEVAL_TOP_K=4
RAG_SCORE_THRESHOLD=0.55
```

Never commit `.env` or API keys.

## Ingest Support Documents

The source files are in `data/`. Ingestion loads them, splits them into searchable chunks, creates embeddings, and stores them in local ChromaDB.

Run incremental ingestion from `backend`:

```powershell
python -m scripts.ingest_documents
```

Incremental ingestion preserves existing records and upserts stable chunk IDs.

To intentionally rebuild the collection:

```powershell
python -m scripts.ingest_documents --rebuild
```

Use `--rebuild` carefully because it resets the local collection before indexing again.

Search indexed support documents:

```powershell
python -m scripts.search_documents "What does DTC code P10301 mean?"
python -m scripts.search_documents "Why is my map not working?" --limit 4
```

## Start the Backend

Start one backend process on all network interfaces:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Use one worker for this POC. Multiple stale processes on port `8000` can cause one client to receive old routes or old code.

Health check:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

## Backend API

### Health

```http
GET /health
```

### Chat

```http
POST /chat
Content-Type: application/json
```

Example request:

```json
{
  "query": "Why is my map not working?"
}
```

The response contains the answer, source metadata, retrieved chunk count, FAQ suggestions, and whether the exact FAQ layer matched.

### Create a ticket

```http
POST /tickets
Content-Type: application/json
```

Example request:

```json
{
  "title": "Map issue",
  "description": "The navigation is not working on my vehicle.",
  "source": "manual"
}
```

Example response:

```json
{
  "reference_id": "TKT-000001",
  "status": "submitted"
}
```

### Admin metrics

```http
GET /admin/metrics?days=30
```

This returns question totals, token totals, estimated cost, latency, retrieval latency, ticket count, recent questions, and model usage.

## How Answering Works

The backend processes a question in this order:

1. Reject an empty question.
2. Detect a simple greeting such as `hi` or `hello`.
3. Check the exact FAQ list in `backend/app/rag/faq.py`.
4. If it is not an exact FAQ question, search ChromaDB.
5. Send retrieved support-document context to Gemini.
6. Return a grounded answer and source metadata.
7. Record chat telemetry in SQLite.

FAQ answers were generated from the existing support-document retrieval flow and then stored as stable approved text. Exact matching avoids unnecessary model calls and prevents broad words such as `app`, `sync`, or `screen` from routing unrelated questions to the wrong FAQ answer.

Normal non-FAQ questions continue through retrieval and generation.

## Android SDK

The reusable SDK is under:

```text
android-sdk/ff-assistant-sdk/
```

Important components:

- `ChatActivity.kt`: chat screen, chips, feedback, tickets, theme, voice input
- `ChatRepository.kt`: cached messages, suggestions, chat requests, ticket requests
- `AssistantApi.kt`: Retrofit API contract
- `AssistantService.kt`: failure-safe network wrapper
- `activity_chat.xml`: chat screen layout
- `item_message_assistant.xml`: assistant response card
- `dialog_ticket_manual.xml`: manual ticket form
- `dialog_ticket_review.xml`: chat-generated ticket review form
- `dialog_ticket_success.xml`: ticket confirmation dialog
- `dialog_rating.xml`: resolution rating dialog

The SDK caches up to the latest 100 messages in app-private SharedPreferences.

## Android Sample App

Move to the Android project:

```powershell
Set-Location "C:\Users\ThreshikaVij_5jgvhlh\OneDrive - RayReach Technologies Pvt. Ltd\Documents\FFAgent\android-sdk"
```

For an Android emulator:

```powershell
.\gradlew.bat :sample-app:assembleDebug -PffBackendUrl="http://10.0.2.2:8000/" --console=plain
```

For the current physical phone setup:

```powershell
.\gradlew.bat :sample-app:assembleDebug -PffBackendUrl="http://172.20.10.2:8000/" --console=plain
```

The APK is generated at:

```text
sample-app/build/outputs/apk/debug/sample-app-debug.apk
```

Find connected devices:

```powershell
$Adb = "C:\Users\ThreshikaVij_5jgvhlh\OneDrive - RayReach Technologies Pvt. Ltd\Documents\Android\sdk\platform-tools\adb.exe"
& $Adb devices
```

Install or update the APK:

```powershell
& $Adb install -r ".\sample-app\build\outputs\apk\debug\sample-app-debug.apk"
```

Launch the app:

```powershell
& $Adb shell am start -n com.ffassistant.sample/.MainActivity
```

Clean install:

```powershell
& $Adb uninstall com.ffassistant.sample
& $Adb install ".\sample-app\build\outputs\apk\debug\sample-app-debug.apk"
& $Adb shell am start -n com.ffassistant.sample/.MainActivity
```

## Android User Flow

When the chat opens with no saved conversation:

1. The assistant displays a greeting.
2. Five FAQ chips appear inside the same assistant card.
3. The chips are vertically stacked and left-aligned.
4. The user can tap a chip or type a custom question.

After an answer:

1. The assistant asks whether the issue is resolved.
2. Selecting **Yes** opens the 1-5 rating dialog.
3. Selecting **No** exposes the ticket action.
4. A chat ticket is prefilled with the question and assistant response.
5. A menu ticket starts with empty title and description fields.
6. The user can edit before submitting.
7. The submit button changes to `Submitting...` to prevent duplicate requests.
8. The backend returns the ticket reference.
9. The confirmation dialog displays the reference and supports copying it.

The overflow menu contains:

- Raise a ticket
- Clear conversation
- Dark mode or Light mode

## Ticket Flows

### Ticket from chat

The assistant already knows the user question and answer, so the ticket review dialog is prefilled with both. The user can edit the summary before submission.

### Ticket from the menu

The user receives an empty form containing:

- Issue title
- Description
- Cancel
- Raise ticket

Both flows call `POST /tickets`. The backend stores the ticket in SQLite and returns a server-generated reference such as `TKT-000001`.

## Dashboard

The dashboard is a static frontend under `dashboard/`.

Start it in another PowerShell window:

```powershell
Set-Location "C:\Users\ThreshikaVij_5jgvhlh\OneDrive - RayReach Technologies Pvt. Ltd\Documents\FFAgent\dashboard"
python -m http.server 5173 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:5173/
```

The dashboard calls:

```text
http://127.0.0.1:8000/admin/metrics
```

It refreshes automatically every five seconds and displays:

- Total questions
- Total tokens
- Estimated cost
- Average response speed
- Average retrieval speed
- Ticket count
- Recent question activity
- Model and retrieval information

Keep both the backend and dashboard servers running.

## Storage

### ChromaDB

```text
backend/storage/chroma/
```

Stores document embeddings and searchable chunks.

### SQLite

```text
backend/storage/admin_metrics.sqlite3
```

Stores chat telemetry and submitted support tickets.

This is local POC storage, not a production CRM or ticketing platform.

## Troubleshooting

### Port 8000 is already in use

Find and stop all processes listening on port `8000`:

```powershell
$connections = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
$connections.OwningProcess | Sort-Object -Unique | ForEach-Object {
    Stop-Process -Id $_ -Force
}
```

Verify it is free:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
```

Start one backend:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Android ticket request returns 404

This usually means the phone reached an old backend process. Check the phone-facing OpenAPI route list:

```powershell
$openapi = Invoke-RestMethod http://172.20.10.2:8000/openapi.json
$openapi.paths.PSObject.Properties.Name
```

The output must include `/tickets`. Stop duplicate processes and restart the current backend if it is missing.

### Android cannot reach the backend

Check:

- The phone and computer are on the same Wi-Fi network.
- The backend is running with `--host 0.0.0.0`.
- The Android build uses the correct LAN IP.
- Windows Firewall allows inbound traffic on port `8000`.
- `http://172.20.10.2:8000/health` works from the computer.

### Dashboard says Backend offline

Check both services:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173/
```

The backend and dashboard are separate processes.

### Vector search cannot load embeddings

The embedding model loads on the first retrieval request. If the environment has an incompatible Python or Hugging Face installation, rebuild the virtual environment and reinstall `requirements.txt`. Do not replace retrieved answers with guesses; the support documents remain the source of truth.

## Validation Commands

Backend syntax checks:

```powershell
Set-Location "C:\Users\ThreshikaVij_5jgvhlh\OneDrive - RayReach Technologies Pvt. Ltd\Documents\FFAgent\backend"
python -m py_compile app\main.py app\core\admin_metrics.py app\api\routes\tickets.py app\schemas\tickets.py
```

Backend tests, if `pytest` is installed:

```powershell
python -m pytest -q
```

Compile the Android SDK:

```powershell
Set-Location "C:\Users\ThreshikaVij_5jgvhlh\OneDrive - RayReach Technologies Pvt. Ltd\Documents\FFAgent\android-sdk"
.\gradlew.bat :ff-assistant-sdk:compileDebugKotlin --console=plain
```

Build the full sample app:

```powershell
.\gradlew.bat :sample-app:assembleDebug -PffBackendUrl="http://172.20.10.2:8000/" --console=plain
```

## Current POC Limitations

- Ticket records are stored in local SQLite, not a production CRM.
- Rating UI works locally but rating data is not yet sent to the backend.
- Dashboard access has no authentication.
- Ticket status updates are not implemented.
- Attachments are not implemented.
- Push notifications and email notifications are not implemented.
- Dashboard currently shows ticket count rather than a full ticket-management table.
- The backend should receive authentication and stronger request validation before external deployment.

## Recommended Next Steps

1. Add a backend rating endpoint and store rating events.
2. Add rating KPIs to the dashboard.
3. Add a full ticket list with status filtering.
4. Connect ticket persistence to the actual support or CRM system.
5. Add authentication for the dashboard and ticket APIs.
6. Add attachments for screenshots and vehicle issue evidence.
7. Add automated Android and backend integration tests.

## Safety Notes

- Do not commit `.env` files or API keys.
- Do not expose the admin dashboard publicly without authentication.
- Do not run multiple backend processes on port `8000`.
- Run normal document ingestion incrementally.
- Use `--rebuild` only when intentionally resetting ChromaDB.
