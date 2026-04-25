from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.schemas import ShippingRequest, ShippingResponse
from agents.orchestrator import ShippingOrchestrator
from config.settings import settings

app = FastAPI(
    title="ShipSmart AI — Multi-Agent Shipping Rate Comparator",
    description="Compares FedEx, UPS, and USPS shipping rates using a LangChain multi-agent system.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = ShippingOrchestrator()


@app.get("/")
async def root():
    return {"status": "ShipSmart AI is running", "env": settings.APP_ENV}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/rates", response_model=ShippingResponse)
async def get_shipping_rates(request: ShippingRequest):
    """
    Main endpoint. Accepts package + shipment details,
    returns ranked quotes from FedEx, UPS, and USPS with an AI recommendation summary.
    """
    try:
        result = await orchestrator.get_quotes(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
