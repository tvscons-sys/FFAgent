# Flying Flea Admin Dashboard

This is a separate admin-only frontend. It reads the isolated `GET /admin/metrics` endpoint and never calls the customer `/chat` endpoint directly.

## Preview

```powershell
cd "C:\Users\ThreshikaVij_5jgvhlh\OneDrive - RayReach Technologies Pvt. Ltd\Documents\FFAgent\dashboard"
python -m http.server 5173
```

Open `http://127.0.0.1:5173`.

## Safe live-data design

The existing chat flow queues telemetry after calculating the answer. A daemon worker writes token, cost, latency, retrieval, model, and question events to `backend/storage/admin_metrics.sqlite3`. The customer request does not wait for that disk write. If the collector fails, the customer answer still returns normally.

Set these optional `.env` values to calculate estimated Gemini cost:

```env
GEMINI_INPUT_COST_INR_PER_MILLION=0
GEMINI_OUTPUT_COST_INR_PER_MILLION=0
```

The defaults are zero until you provide the rates for the billing account/model.
