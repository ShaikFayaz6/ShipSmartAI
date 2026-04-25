# ShipSmart AI — Multi-Agent Shipping Rate Comparator

A production-grade AI-powered shipping rate comparator that uses a **LangChain multi-agent architecture** to query FedEx, UPS, and USPS in parallel and return ranked quotes with an AI-generated recommendation.

---

## Architecture

```
React Frontend (Vite + Custom CSS)
        ↓  POST /api/rates
FastAPI Backend (Python 3.11)
        ↓
LangChain Orchestrator Agent
        ↓  asyncio.gather() — parallel execution
   ┌────────────┬────────────┬────────────┐
FedExTool    UPSTool    USPSTool
(Real API)  (Mock)     (Mock)
        ↓
   Result Aggregator (sort by cost)
        ↓
   LLM Summary (GPT-4o-mini or rule-based fallback)
        ↓
   JSON Response → React renders results table
        ↓
AWS Deploy: S3+CloudFront (frontend) | Lambda+API Gateway (backend)
```

---

## Carrier API Status

| Carrier | Status | Notes |
|---|---|---|
| **FedEx** | ✅ Real Sandbox API | OAuth2 client credentials → Rate API v1 |
| **UPS** | 🟡 Mock | Requires business/org account at developer.ups.com |
| **USPS** | 🟡 Mock | Requires business/org account at developer.usps.com |

> Mock rates mirror real carrier pricing structures including fuel surcharges, dimensional weight, and residential fees.

---

## Project Structure

```
shipping-agent/
├── backend/
│   ├── main.py                  # FastAPI app + CORS
│   ├── requirements.txt
│   ├── Dockerfile               # AWS Lambda compatible
│   ├── .env.example             # Copy to .env and fill in keys
│   ├── config/
│   │   └── settings.py          # Env-based config
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response models
│   └── agents/
│       ├── orchestrator.py      # LangChain orchestrator (main brain)
│       ├── fedex_tool.py        # FedEx REST API + OAuth2
│       ├── ups_tool.py          # UPS mock (ready for real API)
│       └── usps_tool.py         # USPS mock (ready for real API)
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx              # Root component + API call
        ├── index.css            # Full design system
        └── components/
            ├── ShippingForm.jsx # Input form with validation
            └── ResultsTable.jsx # Quotes table + AI summary
```

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- FedEx sandbox credentials (free at developer.fedex.com)
- OpenAI API key (optional — for AI summary; falls back to rule-based)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env — add your FEDEX_CLIENT_ID, FEDEX_CLIENT_SECRET, FEDEX_ACCOUNT_NUMBER

# Run
uvicorn main:app --reload --port 8000
```

API will be live at: http://localhost:8000
Swagger docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App will be live at: http://localhost:5173

---

## API Reference

### POST /api/rates

**Request body:**
```json
{
  "origin_zip": "76201",
  "destination_zip": "45152",
  "weight_lbs": 2.0,
  "length_in": 12.0,
  "width_in": 8.0,
  "height_in": 6.0,
  "delivery_days": 3
}
```

**Response:**
```json
{
  "quotes": [
    {
      "carrier": "USPS",
      "service_name": "USPS Ground Advantage",
      "estimated_cost": 7.00,
      "estimated_days": 5,
      "billable_weight": 2.0,
      "dim_weight": 4.18,
      "guaranteed": false,
      "notes": "Simulated rate"
    }
  ],
  "recommended": { ... },
  "ai_summary": "Best value is USPS Ground Advantage at $7.00...",
  "origin_zip": "76201",
  "destination_zip": "45152",
  "actual_weight": 2.0
}
```

---

## AWS Deployment

### Backend → AWS Lambda + API Gateway

```bash
# 1. Build Docker image
cd backend
docker build -t shipsmart-backend .

# 2. Push to AWS ECR
aws ecr create-repository --repository-name shipsmart-backend
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker tag shipsmart-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/shipsmart-backend:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/shipsmart-backend:latest

# 3. Create Lambda function from ECR image
# Set environment variables in Lambda console (FEDEX_CLIENT_ID, etc.)
# Attach API Gateway trigger with CORS enabled

# 4. Update frontend/.env (or vite.config.js proxy)
# VITE_API_URL=https://<api-gateway-id>.execute-api.<region>.amazonaws.com/prod
```

### Frontend → AWS S3 + CloudFront

```bash
cd frontend
npm run build

# Create S3 bucket
aws s3 mb s3://shipsmart-frontend

# Upload build
aws s3 sync dist/ s3://shipsmart-frontend --delete

# Enable static website hosting
aws s3 website s3://shipsmart-frontend --index-document index.html --error-document index.html

# (Optional) Create CloudFront distribution pointing to S3
# This gives you HTTPS + CDN
```

---

## Getting FedEx Sandbox Credentials

1. Go to [developer.fedex.com](https://developer.fedex.com)
2. Create a free account
3. Click **"Create App"**
4. Select **"Sandbox"** environment
5. Add the **"Rate Quotes"** API to your app
6. Copy `Client ID`, `Client Secret`, and `Account Number` to your `.env`

> Switch `FEDEX_BASE_URL` in `config/settings.py` from `apis-sandbox.fedex.com` to `apis.fedex.com` for production.

---

## Extending to Real UPS/USPS APIs

When you have org credentials, replace the `get_rates()` method in each tool:

### UPS (Real)
```python
# In ups_tool.py get_rates():
# 1. POST https://onlinetools.ups.com/security/v1/oauth/token → get bearer token
# 2. POST https://onlinetools.ups.com/api/rating/v2409/rate → get rates
# 3. Parse response and return ShippingQuote objects
```

### USPS (Real)
```python
# In usps_tool.py get_rates():
# 1. POST https://api.usps.com/oauth2/v3/token → get bearer token
# 2. POST https://api.usps.com/prices/v3/base-rates/search → get rates
# 3. Parse response and return ShippingQuote objects
```

The orchestrator and frontend require **zero changes** — just swap the internals of each tool.

---

## Resume Talking Points

- Built a **multi-agent LangChain system** that orchestrates parallel API calls to FedEx, UPS, and USPS using `asyncio.gather()` for concurrent execution
- Implemented **OAuth2 client credentials flow** for FedEx REST API authentication with automatic token caching
- Applied **dimensional weight (DIM) pricing logic** per carrier spec (FedEx/UPS: /139 divisor; USPS: /166)
- Designed an **extensible tool architecture** — UPS and USPS agents are mock-ready, requiring only credential substitution to go live
- Integrated **LLM-powered recommendation summary** (GPT-4o-mini) with deterministic fallback for reliability
- Deployed via **AWS Lambda (containerized) + API Gateway + S3 + CloudFront**

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Custom CSS |
| Backend | FastAPI, Python 3.11 |
| AI Orchestration | LangChain, OpenAI GPT-4o-mini |
| Carrier APIs | FedEx REST API v1, UPS Rating API (mock), USPS Web Tools (mock) |
| Cloud | AWS Lambda, API Gateway, S3, CloudFront, ECR |
| Auth | OAuth2 Client Credentials (FedEx) |
