# Deploy on Vercel

This repo is configured for a single Vercel project:
- Frontend (Vite React) is built from `frontend/`
- Backend (FastAPI) is served by `api/index.py` (Vercel Python Function)

## 1) Push code to GitHub

Push this repository to your GitHub account.

## 2) Create a Vercel project

1. Open Vercel Dashboard.
2. Click **Add New... -> Project**.
3. Import this repository.
4. Keep defaults (the repo already has `vercel.json`).
5. Deploy.

## 3) Add Environment Variables (Vercel -> Project -> Settings -> Environment Variables)

Required:
- `RATE_MODE` = `test` or `live`
- `FEDEX_CLIENT_ID`
- `FEDEX_CLIENT_SECRET`
- `FEDEX_ACCOUNT_NUMBER`
- `SHIPPO_API_KEY`

Optional:
- `OPENAI_API_KEY`
- `ALLOWED_ORIGINS` (comma-separated list, e.g. `https://your-app.vercel.app`)
- `FEDEX_BASE_URL` (override only if needed)

## 4) Redeploy

After saving env vars, trigger a redeploy from Vercel.

## Notes

- Frontend calls backend via same-origin `/api`, so no frontend API URL is needed in Vercel.
- For local dev, keep `frontend/.env` with:
  - `VITE_API_URL=http://localhost:8002`
